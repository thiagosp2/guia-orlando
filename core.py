"""Pure functions for Disney guide. No Streamlit imports; suitable for tests."""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from math import radians, sin, cos, asin, sqrt
import pandas as pd

TZ = ZoneInfo('America/New_York')
PARKS = {
    'Magic Kingdom': '75ea578a-adc8-4116-a54d-dccb60765ef9',
    'Hollywood Studios': '288747d1-8b4f-4a64-867e-ea7c9b27bad8',
    'Animal Kingdom': '1c84a229-8862-4648-9c71-378ddd2c7693',
    'EPCOT': '47f90d2c-e191-4239-a466-5892ef59a88b',
}
LAND_HINTS = {
 'Magic Kingdom': {'Tomorrowland':['space mountain','tron','buzz lightyear','peoplemover','astro orbiter','carousel of progress'],
  'Fantasyland':['seven dwarfs','peter pan','small world','winnie the pooh','dumbo','barnstormer','philharmagic'],
  'Adventureland':['jungle cruise','pirates of the caribbean','magic carpets','tiki'],
  'Liberty Square':['haunted mansion','hall of presidents','liberty square riverboat'],
  'Frontierland':['big thunder','tiana'], 'Main Street U.S.A.':['town square theater','main street vehicles']},
 'Hollywood Studios': {'Galaxy’s Edge':['rise of the resistance','millennium falcon','smugglers run'], 'Toy Story Land':['slinky dog','toy story mania','alien swirling'], 'Sunset Boulevard':['tower of terror','rock']},
 'Animal Kingdom': {'Pandora':['flight of passage','na’vi',"na'vi"], 'Asia':['expedition everest','kali river'], 'Africa':['kilimanjaro safaris','festival of the lion king']},
 'EPCOT': {'World Discovery':['guardians','mission: space','test track'], 'World Nature':['soarin','living with the land','nemo'], 'World Celebration':['spaceship earth','journey into imagination'], 'World Showcase':['remy','ratatouille','frozen ever after','gran fiesta']}
}
LAND_HINTS.update({
 'Universal Studios Florida': {
  'Diagon Alley':['gringotts','hogwarts express'], 'New York':['revenge of the mummy','transformers'],
  'San Francisco':['fast & furious'], 'Springfield':['simpsons','kang & kodos'],
  'World Expo':['men in black'], 'Minion Land':['minion','villain-con'],
  'Hollywood':['bourne','horror make-up'], 'DreamWorks Land':['trolls','shrek','kung fu panda']},
 'Islands of Adventure': {
  'Hogsmeade':['hagrid','forbidden journey','hippogriff','hogwarts express'],
  'Jurassic Park':['velocicoaster','jurassic park river'], 'Marvel Super Hero Island':['hulk','spider-man','doctor doom'],
  'Toon Lagoon':['popeye','dudley'], 'Seuss Landing':['cat in the hat','seuss','one fish'],
  'Skull Island':['reign of kong']},
 'Epic Universe': {
  'Super Nintendo World':['mario kart','donkey kong','yoshi'],
  'Dark Universe':['monsters unchained','curse of the werewolf'],
  'How to Train Your Dragon':['hiccup','dragon racer','fools'],
  'The Wizarding World — Ministry of Magic':['battle at the ministry','le cirque arcanus'],
  'Celestial Park':['stardust racers','constellation carousel']}
})
UNIVERSAL_THRILL = ['velocicoaster','hagrid','hulk','stardust racers','donkey kong','revenge of the mummy','gringotts','jurassic park river','battle at the ministry','monsters unchained']
UNIVERSAL_SIMULATOR = ['mario kart','forbidden journey','transformers','spider-man','simpsons','men in black','minion']

THRILL = ['tron','space mountain','seven dwarfs','big thunder','tiana','guardians','test track','mission: space','tower of terror','rock','slinky dog','expedition everest','flight of passage']
SIMULATOR = ['soarin','star tours','smugglers run','millennium falcon','rise of the resistance','flight of passage','toy story mania']


def category(name):
    n = name.lower()
    if any(t in n for t in THRILL + UNIVERSAL_THRILL): return 'Radical'
    if any(t in n for t in SIMULATOR + UNIVERSAL_SIMULATOR): return 'Simulador'
    return 'Moderada / outra'


def land_for(park, name):
    n = name.lower()
    for land, terms in LAND_HINTS.get(park, {}).items():
        if any(t in n for t in terms): return land
    return 'Área não mapeada'


def valid_wait(v):
    return float(v) if isinstance(v, (int,float)) and not isinstance(v,bool) and 0 <= v <= 600 else None


def coords(item):
    loc = item.get('location') or {}
    if not isinstance(loc,dict): return (None,None)
    lat = loc.get('latitude', loc.get('lat'))
    lon = loc.get('longitude', loc.get('long', loc.get('lng')))
    try:
        lat,lon=float(lat),float(lon)
        if -90<=lat<=90 and -180<=lon<=180 and (lat or lon): return (lat,lon)
    except (TypeError,ValueError): pass
    return (None,None)


def parse_live(payload, park, metadata=None):
    metadata = metadata or {}
    rows=[]
    for ride in payload.get('liveData',[]):
        if not isinstance(ride,dict): continue
        rid = str(ride.get('id') or ride.get('name') or '')
        if not rid: continue
        m = metadata.get(rid,{})
        name=ride.get('name') or m.get('name') or 'Sem nome'
        lat,lon=coords(m)
        if lat is None or lon is None:
            lat,lon=coords(ride)  # Some live feeds include coordinates directly.
        q=ride.get('queue') or {}
        rows.append({'id':rid,'Atração':name,'Área estimada':land_for(park,name),'Perfil':category(name),
                     'Status':ride.get('status') or 'UNKNOWN',
                     'Fila (min)':valid_wait((q.get('STANDBY') or {}).get('waitTime')),
                     'Single Rider (min)':valid_wait((q.get('SINGLE_RIDER') or {}).get('waitTime')),
                     'Atualizado pela fonte':ride.get('lastUpdated'),'latitude':lat,'longitude':lon})
    return pd.DataFrame(rows,columns=['id','Atração','Área estimada','Perfil','Status','Fila (min)','Single Rider (min)','Atualizado pela fonte','latitude','longitude'])


def parse_children(payload):
    result={}
    for item in payload.get('children',[]):
        if not isinstance(item,dict): continue
        rid=str(item.get('id') or '')
        if rid: result[rid]=item
    return result


def haversine_m(a,b):
    if a is None or b is None or any(v is None for v in (*a,*b)): return None
    lat1,lon1,lat2,lon2=map(radians,(*a,*b))
    dlat=lat2-lat1; dlon=lon2-lon1
    return 6371000*2*asin(sqrt(sin(dlat/2)**2+cos(lat1)*cos(lat2)*sin(dlon/2)**2))


def walk_estimate(a,b,detour=1.45,meters_per_min=70):
    """Straight-line * detour factor. NOT actual pedestrian routing."""
    m=haversine_m(a,b)
    return round(m*detour/meters_per_min,1) if m is not None else None


WEIGHTS = {'prioridade': 0.40, 'fila': 0.35, 'caminhada': 0.15, 'tendencia': 0.10}


def rank_rides(df, current_id, priority_ids, done_ids, max_wait, trend=None,
               walk_weight=1.0, walk_lookup=None, must_ids=None, weights=None, allow_must_over_limit=False):
    """Rank with protected must-do rides, then 40/35/15/10 normalized cost.

    Must-do attractions remain eligible above max_wait only if explicitly allowed; they are ranked
    ahead of optional rides. This is a lexicographic constraint, not a bonus.
    Trends are observed changes in minutes, not forecasts.
    """
    trend = trend or {}
    weights = weights or WEIGHTS
    must = set(must_ids or []) - set(done_ids)
    desired = set(priority_ids or []) | must
    available = df[(df['Status'] == 'OPERATING') & df['Fila (min)'].notna()
                   & (~df['id'].isin(done_ids))
                   & ((df['Fila (min)'] <= max_wait) | (df['id'].isin(must) & bool(allow_must_over_limit)))].copy()
    if available.empty:
        return available
    current = df[df['id'] == current_id]
    position = (current.iloc[0]['latitude'], current.iloc[0]['longitude']) if not current.empty else None
    current_area = current.iloc[0]['Área estimada'] if not current.empty else None
    # Missing coordinates must never be presented as a measured 12-minute walk.

    def score(row):
        walk = walk_lookup(current_id, row['id']) if walk_lookup is not None and current_id is not None else None
        if walk is None:
            walk = walk_estimate(position, (row['latitude'], row['longitude']))
        if walk is None and current_id == row['id']:
            walk = 0.0
        # No valid route or coordinates: unknown, not a fabricated fixed duration.
        walk_known = walk is not None
        if not walk_known:
            walk = 12.0  # Ranking-only neutral penalty, never displayed as walking time.
        delta = trend.get(row['id'])
        # Normalize each component to [0,1]; lower is better.
        priority_cost = 0.0 if row['id'] in must else (0.35 if row['id'] in desired else 1.0)
        queue_cost = min(float(row['Fila (min)']) / 120.0, 1.0)
        walk_cost = min(float(walk) / 30.0, 1.0)
        trend_cost = 0.5 if delta is None else min(max((float(delta) + 30) / 60, 0), 1)
        index = 100 * (weights['prioridade'] * priority_cost + weights['fila'] * queue_cost
                       + weights['caminhada'] * walk_cost + weights['tendencia'] * trend_cost)
        return pd.Series({'Caminhada estimada (min)': round(float(walk),1) if walk_known else float('nan'),
                          'Imperdível': row['id'] in must, 'Índice': round(index,2)})

    available = pd.concat([available, available.apply(score, axis=1)], axis=1)
    return available.sort_values(['Imperdível','Índice','Fila (min)'], ascending=[False,True,True])


def predicted_wait(wait, delta, minutes_ahead):
    """Conservative short-horizon estimate; observed delta is NOT a trained forecast."""
    if delta is None or minutes_ahead <= 0:
        return float(wait)
    return round(max(0.0, min(240.0, float(wait) + max(-20.0, min(20.0, float(delta))) * min(minutes_ahead, 90) / 90)), 1)


def plan_day(df, start_id, priorities, done, max_wait, start_time, end_time,
             ride_duration=12, max_stops=12, walk_lookup=None, must_ids=None, trend=None,
             allow_must_over_limit=False):
    """Lookahead planner: protects feasible must-dos while considering queue trends.

    Forecast is a bounded heuristic based on observed recent change, not an API forecast.
    Uses only cached real walks, otherwise geometric estimates. No LL reservations.
    """
    trend = trend or {}
    must = set(must_ids or []) - set(done)
    current, now, visited, rows = start_id, start_time, set(done), []
    for _ in range(max_stops):
        choices = rank_rides(df, current, priorities, visited, max_wait,
                             trend=trend, walk_lookup=walk_lookup, must_ids=must,
                             allow_must_over_limit=allow_must_over_limit)
        if choices.empty: break
        options=[]
        for _, r in choices.iterrows():
            walk=float(r['Caminhada estimada (min)']) if pd.notna(r['Caminhada estimada (min)']) else 12.0  # Planning-only placeholder
            arrival=now+timedelta(minutes=walk)
            ahead=max(0, (arrival-start_time).total_seconds()/60)
            wait=predicted_wait(r['Fila (min)'],trend.get(r['id']),ahead)
            finish=arrival+timedelta(minutes=wait+ride_duration)
            if finish<=end_time:
                options.append((r,walk,wait,arrival,finish))
        if not options: break
        remaining=must-visited
        must_options=[o for o in options if o[0]['id'] in remaining]
        if remaining and must_options:
            # Non-must stops are permitted only if sufficient conservative budget
            # remains for all outstanding feasible must-dos.
            def budget(candidate):
                after=candidate[4]
                remaining_must=remaining-{candidate[0]['id']}
                outstanding=choices[choices['id'].isin(remaining_must)]
                service=sum(float(r['Fila (min)'])+ride_duration for _,r in outstanding.iterrows())
                # Each subsequent walk may take longer than a direct route.
                travel=sum(max(5.0,float(r['Caminhada estimada (min)'])) for _,r in outstanding.iterrows())
                return (end_time-after).total_seconds()/60 - service - travel
            feasible=[o for o in options if budget(o)>=0]
            if feasible:
                # Prefer a must-do unless a short non-must stop saves significant
                # queue time without threatening the remaining must-do budget.
                chosen=min(feasible,key=lambda o:(
                    0 if o[0]['id'] in remaining else 12,
                    float(o[0]['Índice']) + 0.25*o[2],
                    o[4]))
            else:
                chosen=min(must_options,key=lambda o:(o[4],float(o[0]['Índice'])))
        else:
            chosen=min(options,key=lambda o:(float(o[0]['Índice'])+0.25*o[2],o[4]))
        r,walk,wait,arrival,finish=chosen
        rows.append({'Ordem':len(rows)+1,'Atração':r['Atração'],'Área':r['Área estimada'],
                     'Prioridade':'Imperdível' if r['id'] in must else ('Desejada' if r['id'] in priorities else 'Opcional'),
                     'Chegada estimada':arrival.strftime('%H:%M'),
                     'Fila atual (min)':int(float(r['Fila (min)'])),
                     'Fila projetada (min)':round(wait,1),
                     'Caminhada estimada (min)':round(walk,1),
                     'Saída estimada':finish.strftime('%H:%M'),'id':r['id']})
        visited.add(r['id']); current=r['id']; now=finish
    return pd.DataFrame(rows)


def iso_dt(s):
    try: return datetime.fromisoformat(s.replace('Z','+00:00'))
    except (TypeError,ValueError,AttributeError): return None


def history_entities(payload):
    """Park history envelope has entities with opening + history. Accept list or id-keyed dict."""
    ent=payload.get('entities') or []
    if isinstance(ent,dict):
        return [(str(k),v) for k,v in ent.items() if isinstance(v,dict)]
    if isinstance(ent,list):
        return [(str(x.get('id') or x.get('entityId') or x.get('entity',{}).get('id') or ''),x) for x in ent if isinstance(x,dict)]
    return []


def state_at(entity, target, max_staleness_min=120):
    """Return last known complete state as of target, with source timestamp.
    opening may be carried forward from arbitrarily old data: cap staleness.
    """
    opening=entity.get('opening') or {}
    start=iso_dt(opening.get('time'))
    observed=iso_dt(opening.get('observedAt'))
    state={'status':opening.get('status'),'queue':opening.get('queue') or {},'observed':observed}
    if not start or start>target: state={'status':None,'queue':{},'observed':None}
    for row in sorted(entity.get('history') or [],key=lambda x:x.get('time','')):
        moment=iso_dt(row.get('time'))
        if moment is None or moment>target: continue
        state={'status':row.get('status'),'queue':row.get('queue') or {},'observed':moment}
    obs=state['observed']
    if obs is None or (target-obs).total_seconds()>max_staleness_min*60 or obs>target:
        return {'status':None,'wait':None,'observed':obs,'stale':True}
    return {'status':state['status'], 'wait':valid_wait((state['queue'].get('STANDBY') or {}).get('waitTime')),
            'observed':obs,'stale':False}


def historical_snapshot(payload, when_local, metadata=None, max_staleness_min=120):
    metadata=metadata or {}; target=when_local.astimezone(ZoneInfo('UTC'))
    rows=[]
    for rid,entity in history_entities(payload):
        if not rid: continue
        state=state_at(entity,target,max_staleness_min)
        m=metadata.get(rid,{})
        name=entity.get('name') or (entity.get('entity') or {}).get('name') or m.get('name') or rid
        rows.append({'id':rid,'Atração':name,'Status':state['status'] or 'Sem dado confiável',
                     'Fila (min)':state['wait'],'Última observação':state['observed'],
                     'Dados antigos/ausentes':state['stale']})
    return pd.DataFrame(rows,columns=['id','Atração','Status','Fila (min)','Última observação','Dados antigos/ausentes'])


def historical_series(entity, day, interval_minutes=15, max_staleness_min=120):
    points=[]
    start=datetime.combine(day,datetime.min.time(),TZ)
    for mins in range(0,24*60,interval_minutes):
        local=start+timedelta(minutes=mins)
        state=state_at(entity,local.astimezone(ZoneInfo('UTC')),max_staleness_min)
        points.append({'Horário':local,'Fila (min)':state['wait']})
    return pd.DataFrame(points)
