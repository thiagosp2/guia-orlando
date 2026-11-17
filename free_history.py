"""Importadores gratuitos, com validação explícita de colunas e proveniência.

Não atribui minutos a índices de lotação. Nunca inventa dados históricos.
"""
from io import BytesIO
import pandas as pd
import requests

GITHUB_API = 'https://api.github.com/repos/{owner}/{repo}/contents/{folder}'
WDW_OWNER, WDW_REPO = 'chadwambles', 'wdw-wait-times-analysis'
TOURING_REPOS = {
    'Magic Kingdom': 'DisneyMagicKingdomWaitTimes',
    'EPCOT': 'DisneyEpcotWaitTimes',
    'Hollywood Studios': 'DisneyHollywoodStudiosWaitTimes',
    'Animal Kingdom': 'DisneyAnimalKingdomWaitTimes',
}

def _park(name):
    s = str(name).lower().strip().replace('disney\'s ', '').replace('disneys ', '')
    if 'magic kingdom' in s: return 'Magic Kingdom'
    if 'epcot' in s: return 'EPCOT'
    if 'hollywood' in s or 'studios' in s and 'universal' not in s: return 'Hollywood Studios'
    if 'animal kingdom' in s: return 'Animal Kingdom'
    return str(name).strip()

def normalize_history(df, source='', park_hint=None, ride_hint=None):
    """Retorna park-dia ou ride-dia com média de filas ANUNCIADAS.

    Só aceita colunas de tempo em minutos, nunca crowd_level/index.
    """
    d = df.copy()
    d.columns = [str(c).strip().lower() for c in d.columns]
    date_col = next((c for c in ('date','park_date','day','datetime','wait_datetime') if c in d), None)
    value_col = next((c for c in ('avg_posted_wait_min','average_wait_min','avg_wait','avg_wait_minutes','average_wait','mean_wait','mean_wait_minutes','spostmin','wait_minutes_posted') if c in d), None)
    if not date_col or not value_col:
        raise ValueError('Sem data e tempo de espera anunciado em minutos; índice de lotação não é tempo de fila.')
    park_col = next((c for c in ('park','park_name','parkname') if c in d), None)
    if not park_col and not park_hint:
        raise ValueError('Sem identificação de parque no arquivo.')
    d['date'] = pd.to_datetime(d[date_col], errors='coerce').dt.date
    d['avg_posted_wait_min'] = pd.to_numeric(d[value_col], errors='coerce')
    d['park'] = d[park_col].map(_park) if park_col else _park(park_hint)
    ride_col = next((c for c in ('ride','attraction','attraction_name','ride_name') if c in d), None)
    if ride_col or ride_hint:
        d['ride'] = d[ride_col].astype(str) if ride_col else str(ride_hint)
    d = d[d['date'].notna() & d['avg_posted_wait_min'].between(0,600)].copy()
    if d.empty: raise ValueError('Arquivo sem filas válidas.')
    keys=['date','park']+(['ride'] if 'ride' in d else [])
    d=d.groupby(keys,as_index=False)['avg_posted_wait_min'].mean()
    d['source']=source
    return d

def github_list(session, owner, repo, folder='', branch='main', timeout=18):
    url=GITHUB_API.format(owner=owner,repo=repo,folder=folder)
    r=session.get(url,params={'ref':branch},timeout=timeout)
    r.raise_for_status()
    data=r.json()
    if not isinstance(data,list): raise ValueError('A pasta não contém uma listagem pública.')
    return data

def fetch_csv(session, url, timeout=35, max_bytes=25_000_000):
    r=session.get(url,timeout=timeout)
    r.raise_for_status()
    if len(r.content)>max_bytes: raise ValueError('CSV excede limite de 25 MB; importe manualmente.')
    return pd.read_csv(BytesIO(r.content),low_memory=False)

def download_wdw_history(session, max_files=30):
    """Descobre CSVs do projeto Wambles; ignora formatos sem filas em minutos."""
    entries=github_list(session,WDW_OWNER,WDW_REPO,'csv')
    entries=[e for e in entries if e.get('name','').lower().endswith('.csv') and e.get('download_url')]
    # Nomes que indicam séries diárias antes de índices anuais.
    entries.sort(key=lambda e: (not any(k in e['name'].lower() for k in ('daily','calendar','park_day','park-day')),e['name']))
    frames=[]; notes=[]
    for e in entries[:max_files]:
        try:
            d=fetch_csv(session,e['download_url'])
            frames.append(normalize_history(d,source='Wambles/Queue-Times: '+e['name']))
        except (ValueError,KeyError,pd.errors.ParserError,requests.RequestException) as exc:
            notes.append(f"{e['name']}: {str(exc)[:130]}")
    if not frames: notes.append('Nenhum CSV de filas diárias em minutos identificado automaticamente.')
    return pd.concat(frames,ignore_index=True) if frames else pd.DataFrame(),notes

def download_touringplans(session, park, max_files=12):
    """Baixa CSVs por atração do repositório público TouringPlans, sem chave de API."""
    if park not in TOURING_REPOS: raise ValueError('Parque Disney não reconhecido.')
    repo=TOURING_REPOS[park]
    try: entries=github_list(session,'TouringPlans',repo,branch='master')
    except requests.HTTPError: entries=github_list(session,'TouringPlans',repo,branch='main')
    entries=[e for e in entries if e.get('name','').lower().endswith('.csv') and e.get('download_url')]
    frames=[]; notes=[]
    for e in entries[:max_files]:
        try:
            d=fetch_csv(session,e['download_url'])
            frames.append(normalize_history(d,source='TouringPlans: '+e['name'],park_hint=park,ride_hint=e['name'].rsplit('.',1)[0]))
        except (ValueError,KeyError,pd.errors.ParserError,requests.RequestException) as exc:
            notes.append(f"{e['name']}: {str(exc)[:130]}")
    if not frames: notes.append('Nenhum CSV de filas compatível encontrado no repositório.')
    return pd.concat(frames,ignore_index=True) if frames else pd.DataFrame(),notes

def park_day_dataset(frames):
    """Une fontes com precedência explícita: uma única fonte por parque-dia.

    Não mistura médias de atrações selecionadas com médias de parque completo.
    """
    valid=[f for f in frames if f is not None and not f.empty]
    if not valid: return pd.DataFrame(columns=['date','park','avg_posted_wait_min','source'])
    parts=[]
    for f in valid:
        d=f.copy()
        if 'source' not in d:d['source']='Chart the Magic / importação manual'
        if 'ride' in d:
            d=d.groupby(['date','park','source'],as_index=False)['avg_posted_wait_min'].mean()
        parts.append(d[['date','park','avg_posted_wait_min','source']])
    merged=pd.concat(parts,ignore_index=True)
    # Prefer Wambles park-day data over selected TouringPlans attractions for same day.
    merged['_rank']=merged['source'].astype(str).str.contains('Wambles',case=False).map({True:0,False:1})
    merged=merged.sort_values(['date','park','_rank','source']).drop_duplicates(['date','park'])
    return merged.drop(columns=['_rank']).reset_index(drop=True)
