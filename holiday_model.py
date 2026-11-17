"""Transparent calendar and historical posted-wait estimates, no paid API.

Source CSV: https://chartthemagic.com/open-data/ (CC BY 4.0).
Daily observations do not provide hour-specific holiday forecasts.
"""
from datetime import date, timedelta
import math
import pandas as pd

PARK_NAMES = {
    'Magic Kingdom':'Magic Kingdom', 'EPCOT':'EPCOT',
    'Hollywood Studios':'Hollywood Studios', 'Animal Kingdom':'Animal Kingdom',
    'Islands of Adventure':'Islands of Adventure',
    'Universal Studios Florida':'Universal Studios Florida', 'Epic Universe':'Epic Universe',
}

def thanksgiving(year):
    first=date(year,11,1)
    return first+timedelta(days=(3-first.weekday())%7+21)

def holiday_context(day):
    t=thanksgiving(day.year)
    delta=(day-t).days
    if delta==0:return 'Thanksgiving', 'elevado'
    if delta==1:return 'Black Friday', 'elevado'
    if delta in (-1,2,3):return 'Entorno de Thanksgiving', 'elevado'
    if -4<=delta<=5:return 'Semana de Thanksgiving', 'moderado'
    if day.month==12 and day.day in (24,25,26,31):return 'Natal / Ano-Novo', 'elevado'
    if day.month==1 and day.day in (1,2):return 'Ano-Novo', 'elevado'
    if day.weekday()>=5:return 'Fim de semana', 'moderado'
    return 'Sem alerta especial', 'normal'

def clean_daily(df):
    required={'date','park','ride','avg_posted_wait_min','readings'}
    missing=required-set(df.columns)
    if missing:raise ValueError('CSV sem colunas: '+', '.join(sorted(missing)))
    data=df.copy()
    data['date']=pd.to_datetime(data['date'],errors='coerce').dt.date
    data['avg_posted_wait_min']=pd.to_numeric(data['avg_posted_wait_min'],errors='coerce')
    data['readings']=pd.to_numeric(data['readings'],errors='coerce')
    data=data[data['date'].notna() & data['avg_posted_wait_min'].between(0,600) & (data['readings']>=3)].copy()
    data['park']=data['park'].astype(str).str.strip()
    data['ride']=data['ride'].astype(str).str.strip()
    data=data[data['ride'].ne('')]
    return data.drop_duplicates(['date','park','ride'],keep='last')

def estimate_daily(data,park,target,ride=None,min_days=3):
    """Use daily attraction averages, prefer same weekday; never manufacture holiday uplift."""
    subset=data[data['park'].str.casefold()==park.casefold()].copy()
    if ride:subset=subset[subset['ride'].str.casefold()==ride.casefold()]
    if subset.empty:return None
    subset=subset[subset['date']<target].copy()
    if subset.empty:return None
    subset['weekday']=subset['date'].map(lambda d:d.weekday())
    same=subset[subset['weekday']==target.weekday()]
    matched=same if same['date'].nunique()>=min_days else subset
    if matched['date'].nunique()<min_days:return None
    # Equal weighting by day, avoiding popular rides with more readings dominating.
    days=matched.groupby('date')['avg_posted_wait_min'].mean()
    values=days.sort_values()
    baseline=float(values.median())
    low=float(values.quantile(.2));high=float(values.quantile(.8))
    label,risk=holiday_context(target)
    # Only report measured holiday effect if multiple historical holiday dates exist.
    # Never apply arbitrary multiplier to a point forecast.
    return {'baseline':round(baseline,1),'low':round(low,1),'high':round(high,1),
            'days':len(values),'attractions':matched['ride'].nunique(),
            'calendar':label,'risk':risk,'weekday_matched':matched is same,
            'holiday_adjusted':False}

def comparison(data,parks,start,end):
    rows=[]
    for i in range((end-start).days+1):
        day=start+timedelta(days=i)
        for park in parks:
            e=estimate_daily(data,park,day)
            label,risk=holiday_context(day)
            rows.append({'Data':day,'Parque':park,'Evento':label,'Alerta calendário':risk,
                         'Fila base (min)':e['baseline'] if e else None,
                         'Faixa histórica inferior':e['low'] if e else None,
                         'Faixa histórica superior':e['high'] if e else None,
                         'Dias observados':e['days'] if e else 0,
                         'Estimativa feriado (min)':None})
    return pd.DataFrame(rows)
