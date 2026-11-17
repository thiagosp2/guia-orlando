"""Historical weekday comparisons. No assumption that last month's queues predict holidays."""
from datetime import datetime, time, timedelta
import pandas as pd
from core import TZ, history_entities, state_at

WEEKDAYS=['Segunda','Terça','Quarta','Quinta','Sexta','Sábado','Domingo']

def day_metric(payload, day, preferred_ids=(), hours=range(10,19), stale_min=90,
               selected_ids=None):
    """Historical hourly waits for selected rides, or all rides when selection is empty.

    Unavailable/closed attractions are missing observations, never zero waits.
    Return coverage to disclose how representative the observed mean is.
    """
    entities=[(rid,e) for rid,e in history_entities(payload) if rid]
    if not entities:return None
    selected=set(selected_ids or [])
    filtered=[(rid,e) for rid,e in entities if not selected or rid in selected]
    if not filtered:return None
    preferred=set(preferred_ids or [])
    hourly=[]; preferred_hourly=[]; coverage=[]
    for hour in hours:
        target=datetime.combine(day,time(hour,0),TZ).astimezone(__import__('datetime').timezone.utc)
        valid=[]; fav=[]
        for rid,entity in filtered:
            state=state_at(entity,target,stale_min)
            if state['status']!='OPERATING' or state['wait'] is None:continue
            valid.append(float(state['wait']))
            if rid in preferred:fav.append(float(state['wait']))
        coverage.append(len(valid))
        if valid:hourly.append(float(pd.Series(valid).mean()))
        if fav:preferred_hourly.append(float(pd.Series(fav).mean()))
    if len(hourly)<max(3,len(list(hours))//2):return None
    return {'media_filas':round(sum(hourly)/len(hourly),1),
            'media_prioritarias':round(sum(preferred_hourly)/len(preferred_hourly),1) if preferred_hourly else None,
            'horas_validas':len(hourly),
            'atracoes_medias':round(sum(coverage)/len(coverage),1),
            'atracoes_alvo':len(filtered),
            'atracoes_solicitadas':len(selected) if selected else len(filtered),
            'cobertura_pct':round(100*sum(coverage)/(len(coverage)*len(filtered)),1)}

def weekday_baselines(records):
    """Equal weight per observed day; require at least one valid day per weekday."""
    if not records:return pd.DataFrame()
    df=pd.DataFrame(records)
    if 'cobertura_pct' not in df: df['cobertura_pct']=float('nan')
    df['dia_semana']=df['data'].apply(lambda x:x.weekday())
    return df.groupby(['parque','dia_semana'],as_index=False).agg(
        fila_media=('media_filas','mean'),
        dias_amostrados=('media_filas','size'),
        atracoes_medias=('atracoes_medias','mean'),
        prioridade_media=('media_prioritarias','mean'),
        cobertura_media=('cobertura_pct','mean'))

def recommend_dates(baselines, start, end, parks, preference_weight=0.4):
    """Choose distinct visit dates, one per park, based on sampled weekday baselines.

    Exhaustive search for up to four parks; minimize normalized wait scores so
    a high-wait park does not dominate solely because its scale is larger.
    """
    if baselines.empty:return []
    days=[start+timedelta(days=i) for i in range((end-start).days+1)]
    if len(days)<len(parks):return []
    lookup={(r.parque,int(r.dia_semana)):r for r in baselines.itertuples()}
    candidates={}
    for park in parks:
        vals=baselines[baselines.parque==park]
        if vals.empty:return []
        scale=max(float(vals.fila_media.median()),1.0)
        options=[]
        for d in days:
            row=lookup.get((park,d.weekday()))
            if row is None:continue
            queue=float(row.fila_media)
            preferred=getattr(row,'prioridade_media',None)
            pref=float(preferred) if pd.notna(preferred) else queue
            score=((1-preference_weight)*queue+preference_weight*pref)/scale
            options.append((score,d,queue,int(row.dias_amostrados)))
        if not options:return []
        candidates[park]=sorted(options)
    best=None
    def visit(idx, used, plan, cost):
        nonlocal best
        if best is not None and cost>=best[0]:return
        if idx==len(parks):
            best=(cost,list(plan));return
        park=parks[idx]
        for score,d,queue,n in candidates[park]:
            if d in used:continue
            visit(idx+1,used|{d},plan+[(park,d,queue,n)],cost+score)
    visit(0,set(),[],0.0)
    return sorted(best[1],key=lambda x:x[1]) if best else []

def recommend_date_options(baselines, start, end, parks, limit=2, preference_weight=0.0):
    """Rank weekdays PER PARK, then assign non-colliding actual dates.

    Option 1 takes each park's best supported weekday where feasible;
    option 2 takes the best *different weekday* for every park. A second
    occurrence of the same weekday never counts as an alternative.
    """
    if baselines is None or baselines.empty or end < start or not parks or limit < 1:
        return []
    dates=[start+timedelta(days=i) for i in range((end-start).days+1)]
    if len(dates)<len(parks):return []
    candidates={}
    for park in parks:
        group=baselines[baselines.parque==park]
        if group.empty:return []
        scale=max(float(group.fila_media.median()),1.0)
        weekday_rows={}
        for r in group.itertuples():
            wd=int(r.dia_semana)
            if not any(d.weekday()==wd for d in dates):continue
            queue=float(r.fila_media)
            if not pd.notna(queue):continue
            preferred=getattr(r,'prioridade_media',None)
            pref=float(preferred) if pd.notna(preferred) else queue
            score=((1-preference_weight)*queue+preference_weight*pref)/scale
            weekday_rows[wd]=(score,queue,int(r.dias_amostrados))
        if not weekday_rows:return []
        # Rank is based on the park's own historic waits, not global itinerary score.
        ranked=sorted(weekday_rows,key=lambda wd:(weekday_rows[wd][0],wd))
        candidates[park]=[(rank,wd,*weekday_rows[wd]) for rank,wd in enumerate(ranked)]

    def solve(previous=None):
        best=None
        def walk(i,used,chosen,rank_cost,wait_cost):
            nonlocal best
            if i==len(parks):
                ordered=sorted(chosen,key=lambda x:x[1])
                key=tuple((p,d.isoformat()) for p,d,_,_ in ordered)
                candidate=((rank_cost,round(wait_cost,8),key),ordered)
                if best is None or candidate[0]<best[0]:best=candidate
                return
            park=parks[i]
            for rank,wd,score,queue,n in candidates[park]:
                if previous is not None and wd==previous[park]:continue
                for d in dates:
                    if d.weekday()!=wd or d in used:continue
                    walk(i+1,used|{d},chosen+[(park,d,queue,n)],rank_cost+rank,wait_cost+score)
        walk(0,set(),[],0,0.0)
        return best[1] if best else None

    first=solve()
    if first is None:return []
    plans=[first]
    if limit>=2:
        previous={park:day.weekday() for park,day,_,_ in first}
        second=solve(previous)
        if second is not None:plans.append(second)
    return plans[:limit]
