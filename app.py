"""Disney Guia Virtual v8 — Valhalla público, sem Docker."""
import os
os.environ.setdefault("ORLANDO_PUBLIC_MODE", "1")  # Isolate each visitor
import json
import hashlib
from time import perf_counter
from concurrent.futures import ThreadPoolExecutor, as_completed
import ssl
import sqlite3
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import routing
from park_map import make_park_map, valid_point
from planner_cache import collect_history
from forecast import forecast_wait, queue_alerts
from weekday_optimizer import best_hours, DAYS, holiday_window
from planned_itinerary import plan_ride_hours, optimize_ride_route, itinerary_pdf
from on_demand_routes import optimize_on_demand
from history_analytics import normalize, filter_history, daily_stats, weekday_stats, hourly_stats, date_comparison
from holiday_model import clean_daily, estimate_daily, comparison, holiday_context
from holiday_comparison import compare_holiday_years
from free_history import download_wdw_history, download_touringplans, park_day_dataset, normalize_history
from crowd_model import park_days, forecast_park, attraction_estimates
from period_history import period_waits, summarize_period, WEEKDAYS_PT
from opportunity import build_baselines, rank_opportunities
from day_optimizer import WEEKDAYS, day_metric, weekday_baselines, recommend_dates, recommend_date_options
from decision_engine import collect_day_metrics, weekday_summary, ordered_weekdays
import requests
import streamlit as st
from saved_views import restore as restore_params, save as save_params, clear as clear_params
try:
    import truststore
except ImportError:
    truststore = None  # Use Python default certificate store when unavailable.
from requests.adapters import HTTPAdapter

from core import (PARKS, TZ, parse_live, parse_children, coords as core_coords, rank_rides, plan_day,
                  historical_snapshot, history_entities, historical_series)

API='https://api.themeparks.wiki/v1'
# Mapa claro com ruas, caminhos e rótulos; não requer token Mapbox.
LIGHT_MAP_STYLE='https://basemaps.cartocdn.com/gl/positron-gl-style/style.json'
DB=Path(__file__).parent/'wait_history.sqlite3'
st.set_page_config(page_title='Guia Orlando — Disney + Universal',page_icon='🎢',layout='wide')
restore_params(st.session_state)
# On public hosting, saved selections are per-session only, never shared globally.

st.markdown('''<style>
@media(max-width: 640px) {
  .block-container {padding-top: 1rem; padding-left: .7rem; padding-right: .7rem;}
  div[data-testid="stMetric"] {padding: .35rem;}
  div.stButton > button {min-height: 3.2rem; font-size: 1rem;}
  div[data-testid="stHorizontalBlock"] {gap: .45rem;}
  div[data-testid="stDataFrame"] {max-width: 100%; overflow-x: auto;}
  div[data-testid="stTabs"] button {font-size: .8rem; padding: .45rem .5rem;}
  div[data-testid="stTabs"] [data-baseweb="tab-list"] {overflow-x: auto;}
}
</style>''', unsafe_allow_html=True)

class WindowsTrustAdapter(HTTPAdapter):
    def init_poolmanager(self, connections, maxsize, block=False, **kwargs):
        kwargs['ssl_context']=(truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT) if truststore else ssl.create_default_context())
        return super().init_poolmanager(connections,maxsize,block=block,**kwargs)


@st.cache_data(ttl=24 * 3600, show_spinner=False)
def load_free_holiday_history():
    """Coleta automática, limitada e cacheada por 24 horas por instância.

    Retorna apenas dados de filas anunciadas com colunas verificáveis; não
    transforma índices de lotação em minutos nem inventa dados ausentes.
    """
    frames = []
    reports = []
    with requests.Session() as session:
        session.mount('https://', WindowsTrustAdapter())
        try:
            wdw, notes = download_wdw_history(session, max_files=12)
            if not wdw.empty:
                frames.append(wdw)
            reports.append(('Wambles/Queue-Times', len(wdw), notes))
        except (requests.RequestException, ValueError, KeyError, OSError) as exc:
            reports.append(('Wambles/Queue-Times', 0, [str(exc)]))
        for park in ('Magic Kingdom', 'EPCOT', 'Hollywood Studios', 'Animal Kingdom'):
            try:
                tp, notes = download_touringplans(session, park, max_files=6)
                if not tp.empty:
                    frames.append(tp)
                reports.append(('TouringPlans — ' + park, len(tp), notes))
            except (requests.RequestException, ValueError, KeyError, OSError) as exc:
                reports.append(('TouringPlans — ' + park, 0, [str(exc)]))
    return frames, reports


def active_api_key():
    """Use the key entered in the UI, or the environment variable as fallback."""
    try:
        secret = st.secrets.get('THEMEPARKS_API_KEY', '')
    except (FileNotFoundError, KeyError):
        secret = ''
    return (st.session_state.get('api_key_input') or os.getenv('THEMEPARKS_API_KEY', '') or secret).strip()


def auth_cache_token():
    """Cache discriminator without storing the raw key in cache arguments."""
    key = active_api_key()
    return hashlib.sha256(key.encode()).hexdigest() if key else 'anonymous'


def api_get(path,params=None):
    with requests.Session() as session:
        session.mount('https://',WindowsTrustAdapter())
        key=active_api_key()
        if key: session.headers['X-API-Key']=key
        res=session.get(f'{API}{path}',params=params,timeout=35)
        if res.status_code in (403,429):
            try: info=res.json()
            except ValueError: info={}
            error=info.get('error') or {}
            if res.status_code==403:
                earliest=error.get('earliestAllowedDate','não informada')
                raise RuntimeError(f'Acesso negado ao histórico (HTTP 403). Data mais antiga autorizada: {earliest}. Verifique se a chave foi aceita e se a data está no período do seu plano.')
            retry=res.headers.get('Retry-After',error.get('retryAfter','não informado'))
            raise RuntimeError(f'Limite de consultas atingido (HTTP 429). Tente novamente após {retry} segundos.')
        res.raise_for_status()
        return res.json()

@st.cache_data(ttl=75,show_spinner=False)
def fetch_live(pid,auth_token): return api_get(f'/entity/{pid}/live')

@st.cache_data(ttl=3600,show_spinner=False)
def fetch_children(pid,auth_token): return parse_children(api_get(f'/entity/{pid}/children'))

@st.cache_data(ttl=1800,show_spinner=False)
def fetch_schedule(pid,auth_token): return api_get(f'/entity/{pid}/schedule')

@st.cache_data(ttl=1800,show_spinner=False)
def fetch_history(pid,day,auth_token):
    # A park /history request is limited to one park-local calendar day.
    return api_get(f'/entity/{pid}/history',{'date':day.isoformat()})




def fetch_history_batch_fast(pid, dates, api_key, max_workers=3):
    """Bounded concurrent history retrieval; never access Streamlit state in workers.

    A date failing to load is reported, never silently replaced by an estimate.
    """
    def one(day):
        with requests.Session() as session:
            session.mount('https://', WindowsTrustAdapter())
            if api_key:
                session.headers['X-API-Key'] = api_key
            response = session.get(f'{API}/entity/{pid}/history',
                                   params={'date': day.isoformat()}, timeout=35)
            if response.status_code == 429:
                raise RuntimeError('HTTP 429: limite da API atingido; tente mais tarde')
            if response.status_code == 403:
                raise RuntimeError('HTTP 403: histórico fora do período autorizado')
            response.raise_for_status()
            return response.json()
    payloads, errors = {}, []
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        tasks = {pool.submit(one, d): d for d in dates}
        for task in as_completed(tasks):
            day = tasks[task]
            try:
                payloads[day] = task.result()
            except (RuntimeError, requests.RequestException, ValueError) as exc:
                errors.append(f'{day:%d/%m/%Y}: {exc}')
    return payloads, errors


def fetch_history_sqlite(parks, days, api_key, progress=None):
    """Use the exact persistent history cache shared with Planejar viagem.

    API calls are only made for missing/expired park-days. Do not cache failures.
    """
    def request_one(park_id, hist_day):
        with requests.Session() as session:
            session.mount('https://', WindowsTrustAdapter())
            if api_key:
                session.headers['X-API-Key'] = api_key
            response = session.get(f'{API}/entity/{park_id}/history',
                                   params={'date': hist_day.isoformat()}, timeout=15)
            if response.status_code in (403, 429):
                raise RuntimeError(f'HTTP {response.status_code}: histórico indisponível ou limite da API')
            response.raise_for_status()
            return response.json()
    return collect_history(parks, days, request_one, max_workers=6, progress=progress, retry_count=1)


def prepare_analysis_observations(payloads, metadata, days, ride_ids=None):
    """Normalize all rides once, then filter rides cheaply on Streamlit reruns."""
    if not payloads:
        return normalize(pd.DataFrame())
    observations = period_waits(payloads, metadata, start_hour=8, end_hour=22,
                                step_minutes=30, max_days=max(30, int(days)), ride_ids=ride_ids)
    return normalize(observations)


UNIVERSAL_NAMES = ('Universal Studios Florida', 'Islands of Adventure', 'Epic Universe')

def _normalize_park_name(name):
    import unicodedata
    value=unicodedata.normalize('NFKD',str(name)).encode('ascii','ignore').decode().casefold()
    return ' '.join(value.replace('universal orlando resort','').replace('universal orlando','').split())

def _universal_label(name):
    n=_normalize_park_name(name)
    if 'islands of adventure' in n: return 'Islands of Adventure'
    if 'epic universe' in n: return 'Epic Universe'
    if 'universal studios florida' in n: return 'Universal Studios Florida'
    return None

@st.cache_data(ttl=86400,show_spinner=False)
def discover_universal_parks(auth_token):
    payload=api_get('/destinations')
    destinations=payload.get('destinations',[]) if isinstance(payload,dict) else payload
    found={}
    for dest in destinations or []:
        if not isinstance(dest,dict): continue
        for item in [dest]+(dest.get('parks') or []):
            if not isinstance(item,dict): continue
            label=_universal_label(item.get('name',''))
            if label and item.get('id'): found[label]=str(item['id'])
    return found

def _wait_db_connection():
    """Short-lived connection, SQLite busy timeout and WAL for concurrent Streamlit sessions."""
    con=sqlite3.connect(DB, timeout=8)
    con.execute('PRAGMA busy_timeout=8000')
    return con


def init_db():
    """Initialize lazily; a locked optional cache must not break live API screens."""
    try:
        with _wait_db_connection() as con:
            con.execute('PRAGMA journal_mode=WAL')
            con.execute('CREATE TABLE IF NOT EXISTS waits (park TEXT, ride_id TEXT, ride_name TEXT, observed_at TEXT, wait_min REAL, PRIMARY KEY (park,ride_id,observed_at))')
        return True
    except sqlite3.OperationalError as exc:
        if 'locked' in str(exc).lower() or 'busy' in str(exc).lower():
            return False
        raise


def save_live(park,df):
    """Best-effort local snapshot: never block ThemeParks.wiki live display."""
    now=datetime.now(timezone.utc)
    bucket=now.replace(minute=now.minute//5*5,second=0,microsecond=0).isoformat()
    values=[(park,str(r['id']),r['Atração'],bucket,float(r['Fila (min)'])) for _,r in df.iterrows() if pd.notna(r['Fila (min)'])]
    if not values:return True
    try:
        with _wait_db_connection() as con:
            con.executemany('INSERT OR IGNORE INTO waits VALUES (?,?,?,?,?)',values)
        return True
    except sqlite3.OperationalError as exc:
        if 'locked' in str(exc).lower() or 'busy' in str(exc).lower():
            return False
        raise


def historical_observations(park, days=30):
    """Read local samples, not remote API history; safe on empty databases."""
    try:
        cutoff=(datetime.now(timezone.utc)-timedelta(days=days)).isoformat()
        with _wait_db_connection() as con:
            return con.execute('SELECT ride_id, observed_at, wait_min FROM waits WHERE park=? AND observed_at>=?',
                               (park,cutoff)).fetchall()
    except sqlite3.Error:
        return []


def local_trends(park):
    try:
        with _wait_db_connection() as con:
            h=pd.read_sql_query('SELECT ride_id,observed_at,wait_min FROM waits WHERE park=?',con,params=(park,))
    except sqlite3.Error:
        return {}
    if h.empty:return {}
    h['observed_at']=pd.to_datetime(h['observed_at'],utc=True)
    now=pd.Timestamp.now(tz='UTC')
    a=h[h.observed_at>=now-pd.Timedelta(minutes=30)].groupby('ride_id').wait_min.median()
    b=h[(h.observed_at>=now-pd.Timedelta(minutes=60))&(h.observed_at<now-pd.Timedelta(minutes=30))].groupby('ride_id').wait_min.median()
    return {rid:float(a[rid]-b[rid]) for rid in a.index.intersection(b.index)}


def regular_hours(payload, target_day):
    """Only public OPERATING hours; exclude EXTRA_HOURS, after-hours events and parties."""
    windows=[]
    for entry in (payload.get('schedule') or []):
        if not isinstance(entry,dict) or entry.get('date')!=target_day.isoformat():
            continue
        if entry.get('type')!='OPERATING':
            continue
        try:
            start=datetime.fromisoformat(entry['openingTime'].replace('Z','+00:00')).astimezone(TZ)
            end=datetime.fromisoformat(entry['closingTime'].replace('Z','+00:00')).astimezone(TZ)
            if end>start:windows.append((start,end))
        except (KeyError,ValueError,TypeError):
            continue
    return sorted(windows)


def selected_hours(payload, target_day, regular_only=True):
    if regular_only:
        return regular_hours(payload,target_day)
    windows=[]
    for entry in payload.get('schedule') or []:
        if not isinstance(entry,dict) or entry.get('date')!=target_day.isoformat():
            continue
        if entry.get('type') not in ('OPERATING','EXTRA_HOURS'):
            continue
        try:
            a=datetime.fromisoformat(entry['openingTime'].replace('Z','+00:00')).astimezone(TZ)
            b=datetime.fromisoformat(entry['closingTime'].replace('Z','+00:00')).astimezone(TZ)
            if b>a: windows.append((a,b))
        except (KeyError,ValueError,TypeError):
            continue
    return sorted(windows)

def historical_sample_hours(schedule_payload, day, regular_only=True, start_hour=10, end_hour=18):
    """Return sampling hours and whether the historical schedule was verified.

    The schedule endpoint generally covers upcoming dates, not archived dates.
    When archived operating hours are absent, use a disclosed daytime proxy,
    never mistake missing schedule metadata for missing historical queue data.
    """
    windows=selected_hours(schedule_payload or {}, day, regular_only)
    if not windows:
        return list(range(start_hour, end_hour+1)), False
    hours=[h for h in range(start_hour,end_hour+1)
           if any(a <= datetime.combine(day,time(h,0),TZ) < b for a,b in windows)]
    return hours, True


def schedule_for_today(payload):
    return regular_hours(payload,datetime.now(TZ).date())


def clamp_to_regular_hours(start,finish,windows):
    """Clamp itinerary to the regular public window, never extend into events."""
    if not windows:return None
    # The schedule normally has one public interval; choose the one with most overlap.
    candidates=[(max(start,a),min(finish,b)) for a,b in windows]
    valid=[(a,b) for a,b in candidates if b>a]
    return max(valid,key=lambda x:(x[1]-x[0]).total_seconds()) if valid else None

st.title('🎢 Guia Orlando')
st.caption('ThemeParks.wiki • Horário de Orlando • Valhalla público opcional, sujeito a limites • Estimativas quando indisponível')
with st.sidebar:
    st.header('Configuração')
    if st.button('🧹 Limpar parâmetros salvos',key='clear_saved_params'):
        clear_params(st.session_state)
        st.rerun()
    st.caption('Site público: filtros mantidos apenas nesta sessão. Nenhum resultado ou chave de API é salvo como preferência.')
    st.subheader('Chave da API (opcional)')
    st.text_input('ThemeParks.wiki API Key', type='password', key='api_key_input',
                  help='Cole sua chave gratuita. Ela fica apenas na sessão atual e não aparece na tela.')
    if active_api_key():
        st.success('Chave configurada para as consultas. O acesso ao histórico depende da validade e do plano.')
    else:
        st.info('Sem chave: o histórico gratuito é mais limitado.')
    st.caption('No Streamlit Cloud, configure THEMEPARKS_API_KEY em App settings → Secrets; localmente, use variável de ambiente.')
    st.subheader('Caminhadas')
    valhalla_url=st.text_input('URL do servidor Valhalla (opcional)', value=os.getenv('VALHALLA_URL',routing.PUBLIC_VALHALLA),
         help='Padrão: servidor público de demonstração, sujeito a limites e indisponibilidade. Pode informar outro servidor.')
    walking_speed=st.slider('Velocidade de caminhada (km/h)',2.5,6.0,4.0,0.5)
    st.caption('Disney e Universal Orlando — escolha o parque abaixo.')
    party=st.number_input('Pessoas',1,20,3)
    max_wait=st.slider('Fila máxima aceita (min)',10,180,90,5)
    allow_must_over_limit=st.checkbox('Permitir imperdíveis acima da fila máxima',value=False,
        help='Desmarcado: limite rígido para todas as atrações. Marcado: somente imperdíveis podem ultrapassá-lo.')
    st.caption('Os tempos de espera não variam automaticamente com o tamanho do grupo.')
    if st.button('🔄 Atualizar filas',use_container_width=True):
        fetch_live.clear()
        st.rerun()
    st.caption('Histórico remoto: 7 dias sem chave; 30 dias com chave gratuita; períodos maiores exigem plano compatível.')

auth_token=auth_cache_token()
try:
    universal_parks=discover_universal_parks(auth_token)
except (requests.RequestException,ValueError,RuntimeError) as exc:
    universal_parks={}
    st.sidebar.warning('Não foi possível consultar o catálogo da Universal. Verifique sua conexão com ThemeParks.wiki.')
PARKS.update(universal_parks)
# The park widget was created earlier in this Streamlit run; show a separate selector
# containing both operators, then use its result consistently throughout the app.
if st.session_state.get('park_all') not in PARKS:
    st.session_state.pop('park_all',None)
park=st.sidebar.selectbox('Selecionar parque (Disney + Universal)',list(PARKS),key='park_all',on_change=save_params,args=(st.session_state,))
pid=PARKS[park]
regular_only=st.sidebar.checkbox('Considerar apenas o horário regular dos parques',value=True,key='regular_only',help='Desmarque para incluir horários EXTRA_HOURS publicados. After Hours com ingresso separado pode não constar no calendário e não é incluído automaticamente.')
area_plan,area_day,area_explore,area_settings=st.tabs([
    '🗓️ Planejar viagem','📍 Meu dia no parque','📊 Explorar dados','⚙️ Configurações e fontes'])
with area_plan:
    tab_mobile=st.container()
with area_day:
    tab_live,tab_route=st.tabs(['🎯 Filas e oportunidades','🗺️ Roteiro e mapa'])
with area_explore:
    tab_analytics,tab_days=st.tabs([
        '📊 Análise integrada','📅 Melhores dias'])
with area_settings:
    tab_about=st.container()


# Fetch live data once; historical browsing remains functional if live is down.
live_error=None
try:
    live_payload=fetch_live(pid,auth_token)
    try:
        meta=fetch_children(pid,auth_token)
    except (requests.RequestException,ValueError,RuntimeError):
        meta=st.session_state.get(f'last_metadata_{pid}', {})  # Retain coordinates on refresh failures.
    if meta:
        st.session_state[f'last_metadata_{pid}']=meta
    df=parse_live(live_payload,park,meta)
    if not df.empty:
        if init_db():
            if not save_live(park,df):
                st.caption('Histórico local temporariamente ocupado; filas atuais disponíveis normalmente.')
        else:
            st.caption('Histórico local temporariamente ocupado; filas atuais disponíveis normalmente.')
        latest={str(r['id']):(str(r['Status']),float(r['Fila (min)']) if pd.notna(r['Fila (min)']) else None)
                for _,r in df.iterrows()}
        old=st.session_state.get(f'previous_queues_{pid}',{})
        if old != latest:
            st.session_state[f'queue_alerts_{pid}']=queue_alerts(old,latest)
            st.session_state[f'previous_queues_{pid}']=latest
except (requests.RequestException,ValueError,RuntimeError) as exc:
    live_error=str(exc);df=pd.DataFrame();meta={}

if not df.empty:
    names=dict(zip(df.id,df['Atração']))
    ids=list(names)
    completed_key=f'completed_{pid}'
    priority_key=f'priority_{pid}'
    must_key=f'must_{pid}'
    if completed_key not in st.session_state:st.session_state[completed_key]=[]
    if priority_key not in st.session_state:st.session_state[priority_key]=[]
    if must_key not in st.session_state:st.session_state[must_key]=[]
    # Process mobile actions before the widgets are instantiated in this rerun.
    pending_key=f'pending_action_{pid}'
    pending=st.session_state.pop(pending_key,None)
    skip_key=f'skipped_{pid}'
    if skip_key not in st.session_state:st.session_state[skip_key]=[]
    if pending and pending.get('ride') in ids:
        rid=pending['ride']
        if pending['action']=='done':
            st.session_state[completed_key]=list(dict.fromkeys(st.session_state[completed_key]+[rid]))
            st.session_state[skip_key]=[x for x in st.session_state[skip_key] if x!=rid]
            st.session_state[f'current_location_{pid}']=rid
            st.session_state.pop(f'd_{pid}',None)
        elif pending['action']=='skip':
            st.session_state[skip_key]=list(dict.fromkeys(st.session_state[skip_key]+[rid]))
        elif pending['action']=='undo_skip':
            st.session_state[skip_key]=[x for x in st.session_state[skip_key] if x!=rid]
    # Import a user-owned JSON backup; never accept arbitrary session-state keys.
    pending_import=st.session_state.pop(f'pending_import_{pid}',None)
    if isinstance(pending_import,dict) and pending_import.get('park_id')==pid:
        for state_key,field in [(completed_key,'completed'),(must_key,'must'),(priority_key,'desired'),(skip_key,'skipped')]:
            vals=pending_import.get(field,[])
            if isinstance(vals,list): st.session_state[state_key]=[x for x in vals if isinstance(x,str) and x in ids]
        loc=pending_import.get('location')
        st.session_state[f'current_location_{pid}']=loc if loc in ids else None
        for widget in (f'd_{pid}',f'must_select_{pid}',f'p_{pid}'):
            st.session_state.pop(widget,None)
    with tab_live:
        planned_today=st.session_state.get('planned_result')
        if planned_today and planned_today.get('rows'):
            st.markdown('#### 🗓️ Acompanhar meu roteiro')
            st.caption('Selecione as atrações concluídas; as filas atuais abaixo permanecem independentes do histórico.')
            today_date=datetime.now(TZ).date().strftime('%d/%m/%Y')
            today_plan=[r for r in planned_today['rows'] if r.get('Parque')==park and r.get('Data')==today_date]
            if today_plan:
                st.info('Roteiro planejado para hoje neste parque.')
                for idx,item in enumerate(today_plan):
                    st.checkbox(f"{item['Horário']} — {item['Atração']}",key=f'v30_done_{pid}_{idx}')
            else:st.caption('Não há atrações deste parque no roteiro planejado.')
        else:st.caption('Monte um roteiro em Planejar viagem para acompanhar as atrações aqui.')
    with tab_live:
        a,b,c,d=st.columns(4)
        a.metric('Atrações retornadas',len(df))
        b.metric('Operando',int((df.Status=='OPERATING').sum()))
        c.metric('Filas disponíveis',int(df['Fila (min)'].notna().sum()))
        d.metric('Concluídas',len(st.session_state[completed_key]))
        must=st.multiselect('⭐ Atrações imperdíveis (protegidas)',ids,default=[x for x in st.session_state[must_key] if x in names],format_func=lambda x:names[x],key=f'must_select_{pid}')
        desired_options=[x for x in ids if x not in must]
        priorities=st.multiselect('Atrações desejadas',desired_options,default=[x for x in st.session_state[priority_key] if x in desired_options],format_func=lambda x:names[x],key=f'p_{pid}')
        st.caption('Pesos: prioridade 40% · fila 35% · caminhada 15% · tendência 10%. Imperdíveis têm precedência entre as elegíveis; ultrapassar o limite de fila exige autorização na barra lateral.')
        done=st.multiselect('Atrações já realizadas',ids,default=[x for x in st.session_state[completed_key] if x in names],format_func=lambda x:names[x],key=f'd_{pid}')
        st.session_state[priority_key]=priorities;st.session_state[must_key]=must;st.session_state[completed_key]=done
        location_key=f'current_location_{pid}'
        if st.session_state.get(location_key) not in [None]+ids:
            st.session_state[location_key]=None
        current=st.selectbox('Onde você está? (use uma atração como referência)',[None]+ids,
                             format_func=lambda x:'Entrada / posição desconhecida' if x is None else names[x],
                             key=location_key)
        if current is None:
            st.caption('Selecione sua localização para calcular a caminhada. Sem localização ou coordenadas válidas, o tempo aparece como indisponível (—), não como 12 minutos.')
        trends=local_trends(park)
        def walking_lookup(a,b):
            if not a or not b: return None
            result=routing.cached(park,a,b)
            return round(result['distance_m']/1000/walking_speed*60,1) if result else None
        rank=rank_rides(df,current,priorities,done,max_wait,trends,walk_lookup=walking_lookup,must_ids=must,allow_must_over_limit=allow_must_over_limit)
        # Oportunidade é relativa ao histórico real da mesma atração, sem usar pico como média.
        baselines=build_baselines(historical_observations(park,days=30))
        rank=rank_opportunities(rank,baselines)
        st.caption('Ordenação por oportunidade: favorece filas abaixo da média histórica da própria atração. '
                   'Com pelo menos 6 amostras em 2 dias, prioriza o mesmo horário (±90 min, Orlando); '
                   'sem cobertura nesse horário, usa o histórico geral e sinaliza essa limitação. '
                   'Imperdíveis, limite de fila e caminhada continuam respeitados.')
        if not baselines:
            st.info('Ainda não há histórico local suficiente para detectar oportunidades. '
                    'A ordem original é mantida até que o aplicativo acumule observações em dias diferentes.')
        # O aviso sobre imperdíveis excluídas é independente da tabela de elegíveis.
        excluded_must=df[df['id'].isin(must) & (df['Status']=='OPERATING') & df['Fila (min)'].notna() & (df['Fila (min)']>max_wait)]
        if not allow_must_over_limit and not excluded_must.empty:
            st.warning(f'{len(excluded_must)} atração(ões) imperdível(is) acima de {max_wait} min foram excluídas pelo limite. Para incluí-las, ative a exceção na barra lateral.')
        if rank.empty:
            st.info('Nenhuma atração disponível atende ao limite de fila e aos demais filtros.')
        else:
            top=rank.iloc[0]
            walk_label=(f"{top['Caminhada estimada (min)']:.1f} min" if pd.notna(top['Caminhada estimada (min)']) else 'indisponível')
            st.success(f"Próxima sugestão: **{top['Atração']}** — fila {int(top['Fila (min)'])} min; caminhada {walk_label}")
            if pd.notna(top['Média histórica (min)']):
                st.caption(f"Histórico: média {top['Média histórica (min)']:.0f} min · "
                           f"P90 {top['Pico histórico P90 (min)']:.0f} min · "
                           f"economia estimada {top['Economia (min)']:+.0f} min · {top['Oportunidade']}")
            # v56: colunas operacionais primeiro, com títulos compactos e larguras controladas.
            rank_cols=['Atração','Área estimada','Fila (min)','Caminhada estimada (min)',
                       'Oportunidade','Média histórica (min)','Economia (min)',
                       'Pico histórico P90 (min)','Perfil','Single Rider (min)',
                       'Imperdível','Base histórica','Índice ajustado']
            compact_rank=rank[rank_cols].head(25).rename(columns={
                'Área estimada':'Área',
                'Caminhada estimada (min)':'Caminhada (min)',
                'Média histórica (min)':'Média hist. (min)',
                'Pico histórico P90 (min)':'Pico hist. P90',
                'Economia (min)':'Economia',
                'Single Rider (min)':'Single Rider',
                'Base histórica':'Base hist.',
                'Índice ajustado':'Índice',
            })
            st.dataframe(compact_rank, hide_index=True, use_container_width=True,
                         height=min(720, 38+35*len(compact_rank)),
                         column_config={
                             'Atração':st.column_config.TextColumn(width='medium'),
                             'Área':st.column_config.TextColumn(width='small'),
                             'Fila (min)':st.column_config.NumberColumn(width='small',format='%.0f'),
                             'Caminhada (min)':st.column_config.NumberColumn(width='small',format='%.1f'),
                             'Oportunidade':st.column_config.TextColumn(width='small'),
                             'Média hist. (min)':st.column_config.NumberColumn(width='small',format='%.0f'),
                             'Economia':st.column_config.NumberColumn(width='small',format='%+.0f'),
                             'Pico hist. P90':st.column_config.NumberColumn(width='small',format='%.0f'),
                         })
            if rank['Caminhada estimada (min)'].isna().any():
                st.caption('Caminhada em branco = coordenadas ou origem indisponíveis; o índice usa penalidade neutra, não um tempo de caminhada medido.')
        st.subheader('Todas as atrações')
        st.dataframe(df[['Atração','Área estimada','Perfil','Status','Fila (min)','Single Rider (min)','Atualizado pela fonte']],hide_index=True,use_container_width=True)
        st.download_button('Exportar filas CSV',df.drop(columns=['latitude','longitude']).to_csv(index=False).encode('utf-8-sig'),f'filas_{park.replace(" ","_")}.csv','text/csv')
    with tab_route:
        st.subheader('Mapa de atrações e caminhada')
        st.caption('Selecione origem e destino. O mesmo mapa mostra as coordenadas de todas as atrações, os nomes das áreas e a rota de pedestres, quando disponível.')
        locs=df.dropna(subset=['latitude','longitude']).copy()
        locs['lat']=pd.to_numeric(locs['latitude'],errors='coerce')
        locs['lon']=pd.to_numeric(locs['longitude'],errors='coerce')
        locs=locs.dropna(subset=['lat','lon'])
        if locs.empty:
            st.warning('A API não retornou coordenadas suficientes para exibir o mapa.')
        else:
            locs=locs[locs.apply(lambda r:valid_point(r['lat'],r['lon']),axis=1)].copy()
            if locs.empty:
                st.warning('Nenhuma coordenada geográfica válida para o mapa.')
            else:
                coord_ids=list(locs['id'])
                coord_names=dict(zip(locs['id'],locs['Atração']))
                start_id=dest_id=None
                if len(coord_ids)>=2:
                    c1,c2=st.columns(2)
                    with c1:
                        start_id=st.selectbox('Origem',coord_ids,format_func=lambda x:coord_names[x],key=f'route_start_{pid}')
                    dest_options=[x for x in coord_ids if x!=start_id]
                    with c2:
                        dest_id=st.selectbox('Destino',dest_options,format_func=lambda x:coord_names[x],key=f'route_dest_{pid}')
                # Mapa sempre renderizado. Somente a rota depende do botão.
                if start_id is not None and dest_id is not None and st.button('🚶 Calcular rota de caminhada',key=f'route_button_{pid}'):
                    a=locs.loc[locs.id==start_id].iloc[0]
                    b=locs.loc[locs.id==dest_id].iloc[0]
                    try:
                        route=routing.fetch_route(valhalla_url,park,start_id,dest_id,
                            (a.lat,a.lon),(b.lat,b.lon),walking_speed)
                        st.session_state[f'route_result_{pid}']=(start_id,dest_id,route)
                    except (requests.RequestException,ValueError,KeyError,TypeError,sqlite3.Error,OSError) as exc:
                        st.session_state[f'route_result_{pid}']=(start_id,dest_id,None)
                        st.warning(f'Não foi possível obter rota de pedestres: {exc}')
                saved=st.session_state.get(f'route_result_{pid}')
                route_points=[]
                if saved and saved[:2]==(start_id,dest_id):
                    route=saved[2]
                    if route and route.get('points'):
                        route_points=route['points']
                        st.success(f"Caminhada: {route['distance_m']:.0f} m • {route['distance_m']/1000/walking_speed*60:.1f} min • {route['source']}")
                    else:
                        st.info('Rota não disponível. O mapa continua mostrando as atrações e áreas, sem inventar trajeto.')
                locations=[{'id':str(r['id']),'name':str(r['Atração']),
                    'lat':float(r['lat']),'lon':float(r['lon']),
                    'area':str(r['Área estimada'])} for _,r in locs.iterrows()]
                map_obj=make_park_map(locations,start_id,dest_id,route_points)
                if map_obj:
                    import streamlit.components.v1 as components
                    components.html(map_obj,height=590,scrolling=False)
                st.caption(f'{len(locations)} atrações com coordenadas. Áreas temáticas identificadas sobre o mapa; '
                    'verde = origem, vermelho = destino, azul = rota de caminhada verificada. '
                    'Áreas estimadas pelos nomes das atrações, não polígonos oficiais. '
                    'Use +/−, a roda do mouse ou arraste o mapa para navegar. Fundo OpenStreetMap quando acessível; sem acesso à rede, é exibida uma base esquemática. Fonte: © OpenStreetMap contributors.')
        st.subheader('Lightning Lane (controle manual)')
        st.text_area('Reservas e horários de retorno',key=f'll_{pid}',placeholder='Ex.: TRON 15:00–16:00; Tiana 11:00–12:00')
        st.caption('Não há consulta nem reserva de Lightning Lane nesta versão. Consulte o aplicativo oficial do parque correspondente.')

else:
    with tab_live:st.error(f'Não foi possível consultar as filas: {live_error or "Sem dados"}')
    with tab_route:st.warning('O roteiro depende dos dados ao vivo; consulte a aba Histórico para pesquisar datas anteriores.')


with tab_mobile:
    st.subheader('🗓️ Roteiro Planejado — parques e atrações')
    st.write('Selecione as atrações de cada parque. O roteiro compara **até 30 dias de filas observadas na ThemeParks.wiki**, '
             'escolhe datas distintas com base nos dias da semana e sugere horários de menor espera por atração.')
    st.caption('É necessário acesso ao histórico de 30 dias na API. O roteiro não usa o histórico local.')
    ca,cb=st.columns(2)
    with ca: planned_start=st.date_input('Primeiro dia disponível',value=date(2026,11,26),key='planned_start',on_change=save_params,args=(st.session_state,))
    with cb: planned_end=st.date_input('Último dia disponível',value=date(2026,12,9),key='planned_end',on_change=save_params,args=(st.session_state,))
    if 'planned_parks' in st.session_state:
        st.session_state['planned_parks']=[p for p in st.session_state['planned_parks'] if p in PARKS]
    planned_parks=st.multiselect('Parques a visitar',list(PARKS),
                                 default=list(PARKS)[:4],key='planned_parks',on_change=save_params,args=(st.session_state,))
    planned_selected={}; planned_names={}; planned_coords={}; catalog_fail=[]
    for planned_park in planned_parks:
        planned_pid=PARKS[planned_park]
        try:
            children=fetch_children(planned_pid,auth_token)
            catalog={str(rid):obj.get('name',str(rid)) for rid,obj in children.items()
                     if obj.get('entityType')=='ATTRACTION'}
            if not catalog:raise ValueError('Sem atrações no catálogo')
            with st.expander(f'🎢 {planned_park} — selecionar atrações'):
                options=sorted(catalog,key=lambda rid:catalog[rid].casefold())
                chosen=st.multiselect('Atrações para o roteiro',options,
                    format_func=lambda rid:catalog[rid],key=f'planned_rides_{planned_pid}')
                st.caption(f'{len(chosen)} atração(ões) selecionada(s)')
            planned_selected[planned_park]=list(chosen)
            st.session_state[f'shared_rides_{planned_pid}']=list(chosen)
            planned_names[planned_park]=catalog
            planned_coords[planned_park]={str(rid):core_coords(obj) for rid,obj in children.items()
                if str(rid) in chosen and None not in core_coords(obj)}
        except (ValueError,RuntimeError,requests.RequestException) as exc:
            catalog_fail.append(f'{planned_park}: {exc}')
            planned_selected[planned_park]=[]
    if catalog_fail:st.warning('Catálogo incompleto: '+'; '.join(catalog_fail))
    hour_a,hour_b=st.columns(2)
    with hour_a: planned_first=st.selectbox('Início das atrações',range(8,19),index=2,key='planned_first')
    with hour_b: planned_last=st.selectbox('Último horário de início',range(planned_first+1,23),
                                              index=min(max(18-planned_first-1,0),22-planned_first-1),
                                              key='planned_last')
    buffer_min=st.slider('Margem entre atrações (deslocamento/embarque)',10,40,20,5,
                         key='planned_buffer')
    ride_duration=st.slider('Duração média dentro de cada atração (min) — hipótese ajustável',5,30,12,1,
                            key='planned_ride_duration')
    use_walking=st.checkbox('Otimizar também com rotas reais de caminhada (Valhalla)',value=True,
                            key='planned_use_walking',help='Consulta rotas de pedestres apenas quando existem coordenadas; pares necessários ao roteiro, sob demanda e com cache SQLite. O servidor público pode falhar ou ser lento.')
    st.caption('O roteiro maximiza atrações encaixadas, reduz tempo total estimado e usa apenas caminhadas confirmadas. '
               'A duração de cada atração é uma hipótese configurável; rotas sem resposta permanecem desconhecidas.')
    st.markdown('##### 📅 Terceira opção (opcional): escolha suas datas')
    custom_enabled=st.checkbox('Quero informar datas para uma terceira opção de roteiro',
        key='planned_custom_enabled',value=False)
    custom_dates={}
    if custom_enabled:
        st.caption('Escolha uma data para cada parque. As duas opções recomendadas continuam sendo geradas normalmente.')
        for custom_park in planned_parks:
            custom_dates[custom_park]=st.date_input(
                f'Data desejada — {custom_park}', value=planned_start,
                min_value=planned_start, max_value=max(planned_start,planned_end),
                key=f'planned_custom_date_{PARKS[custom_park]}')
        if len(set(custom_dates.values()))!=len(custom_dates):
            st.warning('A terceira opção precisa de datas distintas para cada parque.')
    valid_selection=(planned_end>=planned_start and
        (planned_end-planned_start).days+1>=len(planned_parks) and
        bool(planned_parks) and all(planned_selected.get(p) for p in planned_parks)
        and not catalog_fail)
    if not valid_selection:
        st.info('Selecione pelo menos uma atração por parque e um intervalo de datas com '
                'pelo menos um dia diferente para cada parque.')
    if st.button('✨ Gerar roteiro com histórico de 30 dias',type='primary',
                 disabled=not valid_selection,key='generate_planned'):
        today=datetime.now(TZ).date()
        dates=[today-timedelta(days=i) for i in range(1,31)]
        timings={}; phase_start=perf_counter()
        records=[]; holiday_records=[]; ride_profiles={}; errors=[]
        progress=st.progress(0)
        # Reutiliza dados brutos persistidos: mudar atrações, datas de visita ou
        # intervalo não refaz as chamadas históricas já concluídas.
        api_key=active_api_key()  # Obtida na thread principal, nunca via Streamlit nos workers.
        def request_history_one(park_id, hist_day):
            with requests.Session() as session:
                session.mount('https://',WindowsTrustAdapter())
                if api_key:session.headers['X-API-Key']=api_key
                response=session.get(f'{API}/entity/{park_id}/history',
                    params={'date':hist_day.isoformat()},timeout=25)
                if response.status_code in (403,429):
                    raise RuntimeError(f'HTTP {response.status_code}: histórico indisponível ou limite da API')
                response.raise_for_status()
                return response.json()
        park_ids=[PARKS[p] for p in planned_parks]
        history_by_id,errors,history_stats=collect_history(
            park_ids,dates,request_history_one,max_workers=6,
            progress=lambda done,total:progress.progress(done/max(total,1)))
        timings['Coleta histórica']=perf_counter()-phase_start
        phase_start=perf_counter()
        for planned_park in planned_parks:
            payloads=history_by_id.get(PARKS[planned_park],{})
            if payloads:
                for hist_day,payload in payloads.items():
                    metric=day_metric(payload,hist_day,(),hours=range(planned_first,planned_last+1),
                                      selected_ids=planned_selected[planned_park])
                    if metric:
                        item={'parque':planned_park,'data':hist_day,**metric}
                        if hist_day in holiday_window(hist_day.year):
                            holiday_records.append(item)
                        else:
                            records.append(item)
                observed=period_waits(payloads,start_hour=planned_first,end_hour=planned_last,
                                      step_minutes=30,max_days=30,
                                      ride_ids=planned_selected[planned_park])
                ride_profiles[planned_park]=[
                    (str(row.id),
                     datetime.combine(row.Data,time.fromisoformat(row.Horário),TZ).isoformat(),
                     float(row[-1])) for row in observed.itertuples(index=False)]
        timings['Tratamento das filas']=perf_counter()-phase_start
        phase_start=perf_counter()
        # Rotas obtidas sob demanda para os trechos consecutivos dos roteiros.
        # A matriz é compartilhada pelas duas opções; SQLite reutiliza os trechos
        # verificados entre execuções. Não há limite fixo de pares por parque.
        walking_matrices={park:{} for park in planned_parks}
        walking_attempted={park:set() for park in planned_parks}
        walking_stats={park:{'consultadas':0,'confirmadas':0,'nao_verificadas':0}
                       for park in planned_parks}
        walking_notes=[]
        timings['Preparação de rotas']=perf_counter()-phase_start
        phase_start=perf_counter()
        # Descartar dias anômalos por parque (MAD robusto), sem fabricar amostras.
        cleaned=[]
        for park_name in planned_parks:
            group=[r for r in records if r['parque']==park_name]
            if len(group)>=6:
                import statistics
                vals=[float(r['media_filas']) for r in group]
                center=statistics.median(vals)
                mad=statistics.median(abs(v-center) for v in vals)
                if mad>0:
                    group=[r for r in group if abs(float(r['media_filas'])-center)<=3.5*1.4826*mad]
            cleaned.extend(group)
        # Relaxar a exigência apenas quando não for possível montar dois planos completos.
        # Preferir sempre dias normais e amostras mais robustas; não inventar filas.
        plan_options=[]; confidence_level=None; use_holiday_fallback=False
        baselines=weekday_baselines(cleaned)
        for min_samples in (3,2,1):
            eligible=(baselines[baselines['dias_amostrados']>=min_samples].copy()
                      if not baselines.empty else baselines)
            candidates=recommend_date_options(eligible,planned_start,planned_end,planned_parks,limit=2)
            if len(candidates)>len(plan_options):
                plan_options=candidates;confidence_level=min_samples
            if len(plan_options)>=2:break
        # Se os 30 dias caírem inteiramente em uma janela de feriado, disponibilizar
        # observações desses dias como último recurso, com aviso explícito.
        if len(plan_options)<2 and holiday_records:
            all_baselines=weekday_baselines(cleaned+holiday_records)
            for min_samples in (3,2,1):
                eligible=(all_baselines[all_baselines['dias_amostrados']>=min_samples].copy()
                          if not all_baselines.empty else all_baselines)
                candidates=recommend_date_options(eligible,planned_start,planned_end,planned_parks,limit=2)
                if len(candidates)>len(plan_options):
                    plan_options=candidates;confidence_level=min_samples;use_holiday_fallback=True
                if len(plan_options)>=2:break
        # Terceira opção: datas informadas pelo usuário, sem alterar o ranking das duas primeiras.
        custom_warning=None
        if custom_enabled and custom_dates and len(set(custom_dates.values()))==len(custom_dates):
            custom_baselines=weekday_baselines(cleaned+holiday_records)
            custom_option=[]
            for custom_park, custom_day in custom_dates.items():
                match=(custom_baselines[(custom_baselines['parque']==custom_park) &
                    (custom_baselines['dia_semana']==custom_day.weekday())]
                    if not custom_baselines.empty else pd.DataFrame())
                if match.empty:
                    custom_option.append((custom_park,custom_day,float('nan'),0))
                else:
                    row=match.iloc[0]
                    custom_option.append((custom_park,custom_day,float(row['fila_media']),int(row['dias_amostrados'])))
            plan_options.append(sorted(custom_option,key=lambda item:item[1]))
            if any(item[3]==0 for item in custom_option):
                custom_warning='Algumas datas escolhidas não possuem histórico comparável; não foram inventadas estimativas de filas.'
        coverage_note=(f'Cobertura histórica: mínimo de {confidence_level} data(s) por parque/dia da semana. '
                       + ('Inclui datas de feriados/eventos históricos, que podem distorcer a previsão. '
                          if use_holiday_fallback else '')
                       + ('Confiança reduzida; compare com os gráficos antes de decidir.'
                          if confidence_level is not None and confidence_level<3 else '')
                       if confidence_level is not None else 'Nenhuma combinação sustentada por observações históricas disponíveis.')

        assignments=plan_options[0] if plan_options else []
        option_details=[]
        for option_index, option_assignments in enumerate(plan_options):
            rows=[]; warnings=[]; option_unverified={}
            if option_index==2 and custom_warning:
                warnings.append(custom_warning)
            for planned_park,visit_day,mean_wait,days_used in option_assignments:
                profile=best_hours(ride_profiles.get(planned_park,[]),
                    planned_selected[planned_park],visit_day.weekday(),
                    planned_first,planned_last,min_days=confidence_level or 3)
                if use_walking:
                    coord_map=planned_coords.get(planned_park,{})
                    def fetch_needed(pair):
                        a,b=pair
                        result=routing.fetch_route(valhalla_url,planned_park,a,b,
                            coord_map[a],coord_map[b],walking_speed)
                        if result:
                            return {**result,'duration_min':round(result['distance_m']/1000/walking_speed*60,1)}
                        return None
                    itinerary,missing,stats=optimize_on_demand(
                        profile,planned_selected[planned_park],planned_names[planned_park],
                        visit_day,planned_park,coord_map,fetch_needed,optimize_ride_route,
                        buffer_min=buffer_min,ride_duration_min=ride_duration,
                        attempted=walking_attempted[planned_park],
                        matrix=walking_matrices[planned_park],max_workers=3)
                    option_unverified[planned_park]=stats['nao_verificadas']
                    walking_stats[planned_park]['consultadas']+=stats['consultadas']
                    walking_stats[planned_park]['confirmadas']+=stats['confirmadas']
                    walking_stats[planned_park]['nao_verificadas']+=stats['nao_verificadas']
                else:
                    itinerary,missing=optimize_ride_route(profile,planned_selected[planned_park],
                        planned_names[planned_park],visit_day,planned_park,
                        travel_minutes={},buffer_min=buffer_min,ride_duration_min=ride_duration)
                rows.extend(itinerary)
                if missing:warnings.append(f'{planned_park}: {len(missing)} atração(ões) sem horário '
                                            'suficientemente amostrado ou sem espaço na programação.')
            if use_walking:
                for park_name, count in option_unverified.items():
                    if count:
                        warnings.append(f"{park_name}: {count} trecho(s) sem rota verificada nesta opção; tempos de caminhada desconhecidos.")
            if confidence_level is not None and confidence_level<3:
                warnings.append(f'Cobertura limitada: apenas {confidence_level} data(s) mínimas por dia da semana. As estimativas têm baixa confiança.')
            if use_holiday_fallback:
                warnings.append('Estimativas por dia podem incluir feriados/eventos históricos. Verifique a programação e a lotação prevista.')
            option_details.append({'rows':rows,'warnings':warnings})
        rows=option_details[0]['rows'] if option_details else []
        warnings=option_details[0]['warnings'] if option_details else []
        timings['Otimização e montagem (inclui rotas sob demanda)']=perf_counter()-phase_start
        timings['Total']=sum(timings.values())
        st.session_state['planned_result']={
            'rows':rows,'assignments':assignments,'plan_options':plan_options,'option_details':option_details,'warnings':warnings,'errors':errors,
            'selection':{p:list(r) for p,r in planned_selected.items()},
            'custom_enabled':custom_enabled,'custom_dates':custom_dates,
            'start':planned_start,'end':planned_end,'hours':(planned_first,planned_last),
            'buffer':buffer_min,'walking_speed':walking_speed,'ride_duration':ride_duration,'use_walking':use_walking,'coverage_note':coverage_note,'confidence_level':confidence_level,'holiday_fallback':use_holiday_fallback,
            'timings':timings,'history_stats':history_stats}
    result=st.session_state.get('planned_result')
    if result:
        with st.expander('⏱️ Desempenho do planejamento',expanded=False):
            stats=result.get('history_stats',{})
            if stats:
                c1,c2,c3=st.columns(3)
                c1.metric('Históricos reaproveitados',stats.get('cache_hits',0))
                c2.metric('Consultas à API',stats.get('api_requests',0))
                c3.metric('Consultas com falha',stats.get('failed_requests',0))
            for stage,seconds in result.get('timings',{}).items():
                st.write(f'{stage}: **{seconds:.1f} s**')
            st.caption('Cache histórico persistente de 30 dias; rotas verificadas usam o cache SQLite já existente. '
                       'A primeira execução pode continuar lenta conforme a API e o serviço de rotas.')
        unchanged=(result['selection']==planned_selected and result['start']==planned_start
                   and result['end']==planned_end and
                   result.get('custom_enabled')==custom_enabled and
                   result.get('custom_dates',{})==custom_dates and
                   result['hours']==(planned_first,planned_last) and result['buffer']==buffer_min
                   and result.get('ride_duration')==ride_duration and result.get('use_walking')==use_walking
                   and result.get('walking_speed')==walking_speed)
        if not unchanged:st.warning('As opções foram alteradas. Os resultados abaixo pertencem à seleção anterior; gere novamente.')
        if result['errors']:
            st.warning(f"{len(result['errors'])} consulta(s) históricas falharam. "
                       f"Exemplo: {result['errors'][0]}")
        if not result['assignments']:
            st.error('Não foi possível montar uma programação completa com os dados históricos recebidos. '
                     'Verifique os avisos de consulta, aumente o intervalo de viagem ou tente novamente.')
        else:
            if result.get('confidence_level',3)<3 or result.get('holiday_fallback'):
                st.warning(result.get('coverage_note','Cobertura histórica limitada.'))
            else:
                st.caption(result.get('coverage_note',''))
            st.markdown('#### Opções de dias e parques')
            st.caption('A segunda opção usa um dia da semana diferente para cada parque. Edite os horários e a ordem '
                       'de cada opção separadamente. A terceira opção aparece quando você informa datas.')
            options=result.get('plan_options',[])
            exported=[]
            for option_i,option_assignments in enumerate(options):
                detail=result['option_details'][option_i]
                st.markdown(f"#### {('🥇 1ª opção — melhor combinação' if option_i==0 else '🥈 2ª opção — melhor dia alternativo da semana' if option_i==1 else '📅 3ª opção — datas escolhidas')}")
                dates_table=pd.DataFrame([
                    {'Data':d.strftime('%d/%m/%Y'),'Dia da semana':DAYS[d.weekday()],
                     'Parque':p,'Fila média histórica (min)':round(q,1) if pd.notna(q) else None,'Dias observados':n}
                    for p,d,q,n in option_assignments])
                st.dataframe(dates_table,hide_index=True,use_container_width=True)
                for warning in detail['warnings']:st.warning(warning)
                if detail['rows']:
                    itinerary_table=pd.DataFrame(detail['rows'])
                    itinerary_table.insert(0,'Ordem',range(1,len(itinerary_table)+1))
                    if 'Caminhada (min)' in itinerary_table:
                        itinerary_table['Caminhada (min)']=itinerary_table['Caminhada (min)'].apply(
                            lambda x: f'{float(x):.1f}' if pd.notna(x) else 'Não verificada')
                    st.caption('Caminhada (min) só é exibida quando a rota foi verificada. Edite Horário e Ordem. Alterações manuais não recalculam estimativas '
                               'nem verificam conflitos de agenda.')
                    edited=st.data_editor(itinerary_table,hide_index=True,use_container_width=True,
                        num_rows='fixed',key=f'v34_edit_itinerary_{option_i}',
                        disabled=['Data','Dia','Parque','Atração','Fila típica (min)','Dias observados','Caminhada (min)','Rota verificada','Duração atração (min)'])
                    edited=edited.sort_values(['Data','Parque','Ordem','Horário'],kind='stable')
                    exported.append((option_assignments,edited.drop(columns=['Ordem']).to_dict('records'),detail['warnings']))
                else:
                    st.warning('Sem horários com cobertura suficiente para esta opção.')
                    exported.append((option_assignments,[],detail['warnings']))
            if len(exported)==1:
                st.info('Não há um dia alternativo da semana com cobertura histórica para todos os parques. '
                        'O PDF incluirá apenas a opção disponível e informará essa limitação.')
            if exported:
                first=exported[0]
                alternative=exported[1] if len(exported)>1 else None
                st.download_button('📄 Baixar PDF com as duas opções',
                    itinerary_pdf(first[0],first[1],first[2],alternative=alternative),
                    'roteiro_orlando_opcoes_1_e_2.pdf','application/pdf',key='v34_pdf_both')
                if len(exported)>2:
                    third=exported[2]
                    st.download_button('📄 Baixar PDF da terceira opção',
                        itinerary_pdf(third[0],third[1],third[2]),
                        'roteiro_orlando_opcao_3.pdf','application/pdf',key='v53_pdf_third')
                csv_parts=[]
                for i,(assignments,rows,warnings) in enumerate(exported,1):
                    for row in rows:csv_parts.append({'Opção':i,**row})
                if csv_parts:
                    st.download_button('Baixar CSV com as opções',
                        pd.DataFrame(csv_parts).to_csv(index=False).encode('utf-8-sig'),
                        'roteiro_orlando_todas_opcoes.csv','text/csv',key='v34_csv_both')
            st.caption('Estimativas históricas, não reservas. Caminhadas são consideradas somente quando verificadas pelo serviço de rotas; '
                       'trechos sem rota ficam identificados como não verificados. A duração dos brinquedos é configurável, não medida individualmente. '
                       'Verifique funcionamento, feriados, eventos e Lightning Lane antes da visita.')

with tab_analytics:
    st.subheader('📊 Explorar dados — análise integrada')
    st.caption('Fonte: ThemeParks.wiki, com cache SQLite compartilhado com Planejar viagem. As seleções do planejamento são reutilizadas por parque.')
    analysis_park=st.selectbox('Parque para análise',list(PARKS),
        index=list(PARKS).index(park) if park in PARKS else 0,key='v30_analysis_park')
    analysis_pid=PARKS[analysis_park]
    try:
        analysis_meta=fetch_children(analysis_pid,auth_token)
        analysis_catalog={str(rid):v.get('name',str(rid)) for rid,v in analysis_meta.items()
                          if v.get('entityType')=='ATTRACTION'}
    except (RuntimeError,requests.RequestException,ValueError) as exc:
        analysis_catalog={}
        st.warning(f'Catálogo indisponível: {exc}')
    analysis_options=sorted(analysis_catalog,key=lambda x:analysis_catalog[x].casefold())
    shared=[x for x in st.session_state.get(f'shared_rides_{analysis_pid}',[]) if x in analysis_catalog]
    if st.session_state.get('v30_analysis_park_last')!=analysis_pid:
        st.session_state['v30_analysis_rides']=shared
        st.session_state['v30_analysis_park_last']=analysis_pid
    analysis_rides=st.multiselect('Atrações para comparar',analysis_options,
        format_func=lambda rid:analysis_catalog.get(rid,rid),key='v30_analysis_rides')
    left,right=st.columns(2)
    with left:
        analysis_days=st.number_input('Janela histórica (dias)',min_value=1,max_value=365,
            value=30,help='Acesso a períodos maiores depende do plano da API.',key='v30_analysis_days')
    with right:
        analysis_mode=st.radio('Tratamento dos dados',['filtered','all'],horizontal=True,
            format_func=lambda x:'Histórico filtrado' if x=='filtered' else 'Histórico completo',
            key='v30_analysis_mode')
    st.caption('Primeiro consulta o SQLite; somente dias ausentes ou expirados são buscados na API (até 6 simultâneos). Apenas as atrações selecionadas são processadas.')
    if st.button('🔄 Consultar histórico ThemeParks.wiki',key='v30_load_analysis'):
        today=datetime.now(TZ).date()
        dates=[today-timedelta(days=i) for i in range(1,int(analysis_days)+1)]
        bar=st.progress(0, text='Verificando SQLite e consultando somente datas ausentes...')
        def update_progress(done,total):
            bar.progress(done/max(1,total), text=f'API: {done}/{total} datas pendentes consultadas')
        with st.spinner(f'Consultando até {len(dates)} datas (máximo 6 simultaneamente)...'):
            by_park,errors,stats=fetch_history_sqlite([analysis_pid],dates,active_api_key(),progress=update_progress)
            payloads=by_park.get(analysis_pid,{})
        bar.empty()
        st.session_state['v30_history_remote']={'pid':analysis_pid,'days':analysis_days,
            'payloads':payloads,'errors':errors,'prepared':None,'prepared_rides':None,'stats':stats}
    remote=st.session_state.get('v30_history_remote',{})
    if remote.get('pid')!=analysis_pid or remote.get('days')!=analysis_days:
        st.info('Consulte o histórico para o parque e período selecionados.')
    else:
        payloads=remote.get('payloads',{})
        if remote.get('errors'):
            st.warning(f"{len(remote['errors'])} data(s) indisponível(is). Exemplo: {remote['errors'][0]}")
        stats=remote.get('stats',{})
        st.caption(f"{len(payloads)} datas disponíveis · {stats.get('cache_hits',0)} reutilizadas do SQLite · {stats.get('api_requests',0)} consultas à API · {stats.get('failed_requests',0)} falhas.")
        if payloads:
            raw=remote.get('prepared')
            selected_key=tuple(sorted(analysis_rides))
            if raw is None or remote.get('prepared_rides')!=selected_key:
                with st.spinner('Processando somente as atrações selecionadas...'):
                    raw=prepare_analysis_observations(payloads,analysis_meta,analysis_days,ride_ids=analysis_rides)
                remote['prepared']=raw
                remote['prepared_rides']=selected_key
            filtered=filter_history(raw,analysis_mode)
            n_removed=len(raw)-len(filtered)
            st.caption(f'{len(raw)} observações válidas · {len(filtered)} incluídas · '
                       f'{n_removed} excluídas · {filtered["Data"].nunique()} datas com amostras')
            if analysis_mode=='all' and raw['atipico'].any():
                with st.expander('Datas atípicas identificadas'):
                    st.dataframe(raw.loc[raw['atipico'],['Data','motivo']].drop_duplicates(),
                                 hide_index=True,use_container_width=True)
            if filtered.empty:
                st.info('Sem observações para as atrações selecionadas e o filtro escolhido.')
            else:
                mode_daily,mode_week,mode_hour,mode_compare=st.tabs([
                    'Por data','Por dia da semana','Por horário','Comparar datas'])
                with mode_daily:
                    metric=st.selectbox('Indicador diário',['Mediana (min)','Média (min)'],key='v30_daily_metric')
                    daily=daily_stats(filtered)
                    chart=daily.pivot_table(index='Data',columns='Atração',values=metric,aggfunc='first')
                    st.line_chart(chart,y_label='Tempo de fila (min)')
                    st.dataframe(daily,hide_index=True,use_container_width=True)
                with mode_week:
                    # Shared park-level metric: identical to the weekday ranking and
                    # the planning baseline when park, rides, dates and hours match.
                    shared_rows, shared_errors = collect_day_metrics(
                        {analysis_pid: payloads}, [analysis_park],
                        sorted(payloads), PARKS,
                        {analysis_park: analysis_rides}, hours=range(10,19))
                    shared_rank = ordered_weekdays(shared_rows, analysis_park, minimum_days=3)
                    st.markdown('##### Indicador geral do parque — metodologia unificada')
                    st.caption('Média horária das atrações selecionadas (10h–18h), seguida da média por data e por dia da semana. Cada data tem peso igual. Exige pelo menos 3 datas por dia da semana. O filtro de atípicos abaixo se aplica somente ao gráfico individual por atração.')
                    if shared_rank:
                        st.dataframe(pd.DataFrame([{
                            'Posição': i, 'Dia da semana': WEEKDAYS[int(r['dia_semana'])],
                            'Fila média (min)': round(float(r['fila_media']),1),
                            'Dias observados': int(r['dias_amostrados']),
                            'Cobertura média (%)': round(float(r['cobertura_media']),1),
                        } for i,r in enumerate(shared_rank,1)]), hide_index=True, use_container_width=True)
                    else:
                        st.info('Sem pelo menos 3 datas válidas por dia da semana para o indicador geral.')
                    st.markdown('##### Detalhamento por atração (metodologia individual)')
                    weekly=weekday_stats(filtered)
                    metric=st.selectbox('Indicador semanal',['Mediana (min)','Média (min)'],key='v30_week_metric')
                    minimum=st.number_input('Mínimo de datas por dia da semana',1,30,3,key='v30_week_min')
                    eligible=weekly[weekly['Dias observados']>=minimum].copy()
                    if eligible.empty:st.info('Não há dias da semana com cobertura suficiente.')
                    else:
                        eligible['Dia da semana']=eligible['weekday'].map(lambda i:DAYS[i])
                        chart=eligible.pivot_table(index='weekday',columns='Atração',values=metric)
                        chart.index=[DAYS[i] for i in chart.index]
                        st.bar_chart(chart,y_label='Tempo de fila (min)')
                        st.dataframe(eligible[['Dia da semana','Atração','Mediana (min)',
                            'Média (min)','Dias observados']],hide_index=True,use_container_width=True)
                with mode_hour:
                    weekday=st.selectbox('Dia da semana',list(range(7)),format_func=lambda i:DAYS[i],key='v30_hour_weekday')
                    hours=st.slider('Horário (Orlando)',8,22,(10,18),key='v30_hour_range')
                    metric=st.selectbox('Indicador por horário',['Mediana (min)','Média (min)'],key='v30_hour_metric')
                    hourly=hourly_stats(filtered,weekday=weekday)
                    hourly=hourly[hourly['Horário'].map(lambda x:hours[0]<=int(x[:2])<=hours[1])]
                    hourly=hourly[hourly['Dias observados']>=3]
                    if hourly.empty:st.info('Sem três datas válidas para os horários escolhidos.')
                    else:
                        st.line_chart(hourly.pivot_table(index='Horário',columns='Atração',values=metric),
                                      y_label='Tempo de fila (min)')
                        st.dataframe(hourly,hide_index=True,use_container_width=True)
                with mode_compare:
                    available=sorted(filtered['Data'].unique())
                    selected_dates=st.multiselect('Datas específicas para comparação',available,
                        default=available[-2:] if len(available)>=2 else available,
                        format_func=lambda d:d.strftime('%d/%m/%Y'),key='v30_compare_dates')
                    if selected_dates:
                        comparison=date_comparison(filtered,selected_dates)
                        st.caption('As referências típicas são calculadas usando o mesmo conjunto histórico filtrado ou completo.')
                        st.bar_chart(comparison.pivot_table(index='Referência',columns='Atração',
                            values='Mediana (min)',aggfunc='first'),y_label='Mediana (min)')
                        st.dataframe(comparison,hide_index=True,use_container_width=True)
                    else:st.info('Selecione uma ou mais datas para comparar.')
                st.download_button('⬇️ Exportar observações (CSV)',
                    filtered.to_csv(index=False).encode('utf-8-sig'),
                    f'historico_{analysis_pid}.csv','text/csv',key='v30_export_analytics')

with tab_days:
    st.subheader('📅 Ranking dos melhores dias da semana por parque')
    st.caption('Indicador compartilhado com Planejar viagem e Análise integrada: média das filas por hora, depois por data e dia da semana (10h–18h). Exige 3 datas válidas por dia da semana. Não é previsão de uma data específica.')
    today_orlando = datetime.now(TZ).date()
    default_end = today_orlando - timedelta(days=1)
    default_start = default_end - timedelta(days=29)
    c1, c2 = st.columns(2)
    with c1:
        ranking_start = st.date_input('Início do período histórico', value=default_start, key='v47_ranking_start',on_change=save_params,args=(st.session_state,))
    with c2:
        ranking_end = st.date_input('Fim do período histórico', value=default_end, max_value=default_end, key='v47_ranking_end',on_change=save_params,args=(st.session_state,))
    if 'v47_ranking_parks' in st.session_state:
        st.session_state['v47_ranking_parks']=[p for p in st.session_state['v47_ranking_parks'] if p in PARKS]
    ranking_parks = st.multiselect('Parques', list(PARKS), default=list(PARKS), key='v47_ranking_parks',on_change=save_params,args=(st.session_state,))
    ranking_selected = {}
    with st.expander('🎢 Atrações por parque (opcional)', expanded=False):
        st.caption('Sem seleção: todas as atrações disponíveis. Com seleção: ranking personalizado, usando a mesma métrica do Planejar viagem.')
        for ranking_name in ranking_parks:
            ranking_pid = PARKS[ranking_name]
            try:
                ranking_meta = fetch_children(ranking_pid, auth_token)
                ranking_catalog = {str(rid): obj.get('name',str(rid)) for rid,obj in ranking_meta.items() if obj.get('entityType')=='ATTRACTION'}
                choices = sorted(ranking_catalog, key=lambda rid: ranking_catalog[rid].casefold())
                widget_key = f'v52_ranking_rides_{ranking_pid}'
                if widget_key in st.session_state:
                    st.session_state[widget_key] = [rid for rid in st.session_state[widget_key] if rid in ranking_catalog]
                ranking_selected[ranking_name] = st.multiselect(
                    ranking_name, choices, format_func=lambda rid,cat=ranking_catalog: cat.get(rid,rid),
                    key=widget_key, on_change=save_params, args=(st.session_state,))
            except (requests.RequestException, ValueError, RuntimeError) as exc:
                ranking_selected[ranking_name] = []
                st.warning(f'{ranking_name}: catálogo indisponível ({exc}). Será utilizado o parque inteiro.')
    ranking_filter = (ranking_start,ranking_end,tuple(ranking_parks),
                      tuple((p,tuple(sorted(ranking_selected.get(p,[])))) for p in ranking_parks))
    if ranking_end < ranking_start:
        st.error('O fim do período deve ser igual ou posterior ao início.')
    elif ranking_end >= today_orlando:
        st.error('A análise exige datas passadas; o dia atual ainda não está completo.')
    elif (ranking_end - ranking_start).days > 365:
        st.error('Selecione um período de até 366 dias para evitar consultas excessivas.')
    elif st.button('📊 Calcular ranking', type='primary', key='v47_calcular_ranking'):
        sampled = [ranking_start + timedelta(days=i) for i in range((ranking_end-ranking_start).days+1)]
        progress = st.progress(0)
        histories, errors, metrics = fetch_history_sqlite(
            [PARKS[name] for name in ranking_parks], sampled, active_api_key(),
            progress=lambda done,total: progress.progress(done/max(total,1)))
        progress.empty()
        records, calculation_errors = collect_day_metrics(
            histories, ranking_parks, sampled, PARKS, ranking_selected,
            hours=range(10,19))
        errors.extend(calculation_errors)
        st.session_state['v47_ranking_result']={
            'records':records,'errors':errors,'metrics':metrics,
            'filters':ranking_filter}
    result=st.session_state.get('v47_ranking_result')
    if result:
        if result['filters'] != ranking_filter:
            st.info('O período ou os parques mudaram. Clique em Calcular ranking para atualizar.')
        else:
            m=result['metrics']
            st.caption(f"SQLite: {m['cache_hits']} parque-dia(s) reutilizados · API: {m['api_requests']} consultas · Falhas: {m['failed_requests']}")
            if result['errors']:
                st.warning(f"{len(result['errors'])} consultas ou dias tiveram problemas. Dias sem dados válidos não entram na média.")
                with st.expander('Ver detalhes das falhas'):
                    st.write('\n'.join(result['errors'][:60]))
            baselines=weekday_summary(result['records'], minimum_days=3)
            for park_name in ranking_parks:
                st.markdown(f'#### {park_name}')
                rows=[]
                park_data=baselines[baselines['parque']==park_name] if not baselines.empty else pd.DataFrame()
                for weekday in range(7):
                    match=park_data[park_data['dia_semana']==weekday] if not park_data.empty else pd.DataFrame()
                    if match.empty:
                        rows.append({'Dia da semana':WEEKDAYS[weekday],'Fila média (min)':None,'Dias observados':0})
                    else:
                        r=match.iloc[0]
                        rows.append({'Dia da semana':WEEKDAYS[weekday],
                                     'Fila média (min)':round(float(r['fila_media']),1),
                                     'Dias observados':int(r['dias_amostrados'])})
                valid=sorted((r for r in rows if r['Fila média (min)'] is not None),
                             key=lambda r:(r['Fila média (min)'],WEEKDAYS.index(r['Dia da semana'])))
                ranked=[{'Posição':i,'Dia da semana':r['Dia da semana'],
                         'Fila média (min)':r['Fila média (min)'],'Dias observados':r['Dias observados']}
                        for i,r in enumerate(valid,1)]
                ranked.extend({'Posição':'—','Dia da semana':r['Dia da semana'],
                               'Fila média (min)':None,'Dias observados':0}
                              for r in rows if r['Fila média (min)'] is None)
                st.dataframe(pd.DataFrame(ranked),hide_index=True,use_container_width=True)
            st.caption('Cada data observada tem o mesmo peso na média do seu dia da semana. Filas de atrações fechadas ou sem informação não são consideradas zero. Janela de análise: 10h–18h, horário de Orlando; dias sem amostras suficientes aparecem sem classificação. O acesso a datas antigas depende da API.')


with tab_about:
    st.subheader('⚙️ Configurações e fontes')
    st.info('As configurações de API, caminhada e limites estão na barra lateral. '
            'O histórico da área Explorar utiliza o SQLite compartilhado com Planejar viagem e consulta a API apenas quando necessário.')
    st.caption('MVP29 preservado; v30 usa a mesma integração com a API e o roteador Valhalla opcional.')
with tab_about:
    st.markdown('''**Como o MVP decide:** compara a fila Standby atual, um bônus para atrações prioritárias e caminhada. Quando existe rota de pedestres previamente calculada no Valhalla, utiliza sua distância; caso contrário, recorre à distância em linha reta × 1,45 ou estimativa por área. Isso não garante a existência de caminhos abertos.\n\n**Limitações:** rotas Valhalla dependem de servidor configurado e da qualidade dos dados OpenStreetMap; não há verificação automática de bloqueios, entradas ou saídas de atrações. Não prevê com precisão a evolução real das filas, não conhece sua posição GPS, não integra Lightning Lane e não garante o tempo que você realmente ficará na fila. O histórico da API é independente do histórico local coletado pelo MVP.\n\n**Privacidade:** prioridades e atrações concluídas ficam na sessão Streamlit; o histórico local de observações ao vivo é salvo em SQLite neste computador. A chave da API pode ser informada na barra lateral ou por variável de ambiente e não é exibida na interface.''')
    st.markdown('**Fonte e atribuição:** [Powered by ThemeParks.wiki](https://www.themeparks.wiki/) — serviço independente, não afiliado à Disney ou Universal.')

st.divider()
st.caption('Powered by ThemeParks.wiki — https://www.themeparks.wiki/ • Projeto independente, não afiliado à Disney ou Universal.')

# Save parameter changes after rendering; results are deliberately excluded.
save_params(st.session_state)
