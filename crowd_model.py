"""Modelo transparente de lotação relativa -> espera anunciada (minutos)."""
from datetime import timedelta
import numpy as np
import pandas as pd
from holiday_model import thanksgiving

PARKS = ('Magic Kingdom','EPCOT','Hollywood Studios','Animal Kingdom')

def normalize_park(name):
    s=str(name).lower()
    if 'magic kingdom' in s:return 'Magic Kingdom'
    if 'epcot' in s:return 'EPCOT'
    if 'hollywood' in s:return 'Hollywood Studios'
    if 'animal kingdom' in s:return 'Animal Kingdom'
    return str(name).strip()

def park_days(frames):
    """Um valor por parque/dia; não duplica fontes nem mistura atrações de amostras diferentes."""
    chunks=[]
    for frame in frames:
        if frame is None or frame.empty:continue
        f=frame.copy()
        if not {'date','park','avg_posted_wait_min'}.issubset(f):continue
        f['date']=pd.to_datetime(f.date,errors='coerce').dt.date
        f['park']=f.park.map(normalize_park)
        f['avg_posted_wait_min']=pd.to_numeric(f.avg_posted_wait_min,errors='coerce')
        f=f[f.date.notna() & f.avg_posted_wait_min.between(1,300) & f.park.isin(PARKS)]
        if f.empty:continue
        f['source']=f.source.astype(str) if 'source' in f else 'Sem identificação'
        if 'ride' in f:
            f=f.groupby(['date','park','source'],as_index=False).avg_posted_wait_min.mean()
            f['sample_type']='atrações selecionadas'
        else:f['sample_type']='média parque'
        chunks.append(f[['date','park','source','avg_posted_wait_min','sample_type']])
    if not chunks:return pd.DataFrame(columns=['date','park','source','avg_posted_wait_min','sample_type','year','crowd_relative'])
    d=pd.concat(chunks,ignore_index=True)
    d['priority']=d.sample_type.map({'média parque':0,'atrações selecionadas':1})
    d=d.sort_values(['park','date','priority','source']).drop_duplicates(['park','date']).drop(columns='priority')
    d['year']=d.date.map(lambda x:x.year)
    # A escala é intra-ano e intra-parque: não usa o crowd level público como minutos.
    group=d.groupby(['park','year']).avg_posted_wait_min
    d['crowd_relative']=group.transform(lambda x:x/x.median() if x.median()>0 else np.nan)
    return d.sort_values(['park','date']).reset_index(drop=True)

def forecast_park(d,park,target,min_years=2):
    """Efeito sazonal relativo para a data alvo, calibrado em minutos recentes.
    Retorna None quando não existem anos comparáveis e baseline recente.
    """
    p=d[d.park==park].copy()
    if p.empty:return None
    offset=(target-thanksgiving(target.year)).days
    effects=[];detail=[]
    for year in sorted(set(p.year)):
        if year>=target.year:continue
        day=thanksgiving(year)+timedelta(days=offset)
        actual=p[p.date==day]
        refs=[day+timedelta(days=i) for i in (-21,-14,-7,7,14,21)]
        normal=p[p.date.isin(refs)]
        if len(actual)!=1 or len(normal)<2:continue
        if actual.iloc[0].sample_type!=normal.iloc[0].sample_type:continue
        baseline=float(normal.avg_posted_wait_min.median())
        if baseline<=0:continue
        effect=float(actual.iloc[0].avg_posted_wait_min/baseline)
        if .25<=effect<=4:
            effects.append(effect)
            detail.append({'Ano':year,'Espera feriado (min)':round(float(actual.iloc[0].avg_posted_wait_min),1),
                           'Referência normal (min)':round(baseline,1),'Fator relativo':round(effect,3)})
    if len(effects)<min_years:return None
    recent=p[(p.date<target)&(p.date>=target-timedelta(days=75))]
    if len(recent)<7:return None
    # Janela sazonal recente: estimativa de escala atual, não previsão de público absoluto.
    baseline=float(recent.avg_posted_wait_min.median())
    if baseline<=0:return None
    factors=np.asarray(effects,dtype=float)
    median=float(np.median(factors))
    return {'park':park,'date':target,'baseline':round(baseline,1),
            'predicted':round(baseline*median,1),
            'low':round(baseline*float(np.quantile(factors,.2)),1),
            'high':round(baseline*float(np.quantile(factors,.8)),1),
            'relative_crowd':round(median,2),'years':len(effects),'recent_days':len(recent),
            'detail':pd.DataFrame(detail),'source_types':sorted(p.sample_type.unique().tolist())}

def attraction_estimates(frames,park,park_forecast,min_days=5):
    """Escala as médias recentes por atração, sem inventar horário individual."""
    rides=[]
    for f in frames:
        if f is None or f.empty or not {'date','park','ride','avg_posted_wait_min'}.issubset(f):continue
        x=f.copy();x['date']=pd.to_datetime(x.date,errors='coerce').dt.date
        x['park']=x.park.map(normalize_park)
        x['avg_posted_wait_min']=pd.to_numeric(x.avg_posted_wait_min,errors='coerce')
        x=x[(x.park==park)&x.avg_posted_wait_min.between(1,300)]
        if not x.empty:rides.append(x)
    if not rides:return pd.DataFrame()
    d=pd.concat(rides,ignore_index=True)
    latest=d.date.max();d=d[d.date>=latest-timedelta(days=75)]
    agg=d.groupby('ride').agg(days=('date','nunique'),avg=('avg_posted_wait_min','median')).reset_index()
    agg=agg[agg.days>=min_days]
    if agg.empty:return pd.DataFrame()
    # Fator do feriado multiplica cada atração; não força média de uma amostra
    # selecionada a coincidir com uma média do parque de outra fonte.
    agg['Fila prevista (min)']=(agg.avg*park_forecast['relative_crowd']).round(0)
    agg['Faixa inferior (min)']=(agg.avg*park_forecast['low']/park_forecast['baseline']).round(0)
    agg['Faixa superior (min)']=(agg.avg*park_forecast['high']/park_forecast['baseline']).round(0)
    return agg.rename(columns={'ride':'Atração','days':'Dias observados','avg':'Fila recente mediana (min)'})[['Atração','Dias observados','Fila recente mediana (min)','Fila prevista (min)','Faixa inferior (min)','Faixa superior (min)']].sort_values('Fila prevista (min)',ascending=False)
