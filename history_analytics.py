"""Shared, source-independent analysis of observed park waits. No fabricated samples."""
from datetime import date, datetime
import pandas as pd
from weekday_optimizer import holiday_window

COLS=['Data','Dia da semana','id','Atração','Horário','Fila (min)']
DAYS=['Segunda','Terça','Quarta','Quinta','Sexta','Sábado','Domingo']

def normalize(observations):
    if observations is None or observations.empty:return pd.DataFrame(columns=COLS+['weekday','atipico','motivo'])
    df=observations.copy()
    df['Data']=pd.to_datetime(df['Data'],errors='coerce').dt.date
    df['Fila (min)']=pd.to_numeric(df['Fila (min)'],errors='coerce')
    df=df.dropna(subset=['Data','Fila (min)','id','Horário'])
    df=df[df['Fila (min)'].between(0,600)].copy()
    df['id']=df['id'].astype(str)
    df['weekday']=df['Data'].map(lambda d:d.weekday())
    # Day-level anomalies: compare park-day median to other days of SAME weekday
    daily=df.groupby('Data')['Fila (min)'].median()
    anomalous=set()
    for wd in range(7):
        group=daily[[d.weekday()==wd for d in daily.index]]
        if len(group)<6:continue
        center=group.median();mad=(group-center).abs().median()
        if mad>0:anomalous.update(d for d,v in group.items() if abs(v-center)>3.5*1.4826*mad)
    df['motivo']=df['Data'].map(lambda d:'Feriado/período especial' if d in holiday_window(d.year) else ('Anomalia estatística' if d in anomalous else ''))
    df['atipico']=df['motivo']!=''
    return df

def filter_history(df,mode='filtered'):
    if mode not in ('filtered','all'):raise ValueError('Modo inválido')
    return df.loc[~df['atipico']].copy() if mode=='filtered' else df.copy()

def daily_stats(df):
    if df.empty:return pd.DataFrame(columns=['Data','id','Atração','Média (min)','Mediana (min)','Amostras'])
    return df.groupby(['Data','id','Atração'],as_index=False).agg(**{
        'Média (min)':('Fila (min)','mean'),'Mediana (min)':('Fila (min)','median'),
        'Amostras':('Fila (min)','size')})

def weekday_stats(df):
    # First aggregate each independent date, then weekday; no sample-frequency bias.
    daily=daily_stats(df)
    if daily.empty:return pd.DataFrame(columns=['weekday','id','Atração','Mediana (min)','Média (min)','Dias observados'])
    daily['weekday']=daily['Data'].map(lambda d:d.weekday())
    return daily.groupby(['weekday','id','Atração'],as_index=False).agg(**{
        'Mediana (min)':('Mediana (min)','median'),'Média (min)':('Média (min)','mean'),
        'Dias observados':('Data','nunique')})

def hourly_stats(df,weekday=None,day=None,bin_minutes=60):
    if bin_minutes not in (15,30,60):raise ValueError('Intervalo inválido')
    work=df.copy()
    if day is not None:work=work[work['Data']==day]
    elif weekday is not None:work=work[work['weekday']==weekday]
    if work.empty:return pd.DataFrame(columns=['id','Atração','Horário','Mediana (min)','Média (min)','Dias observados'])
    minute=pd.to_timedelta(work['Horário']+':00',errors='coerce').dt.total_seconds()/60
    work=work.assign(_slot=(minute//bin_minutes*bin_minutes))
    work=work.dropna(subset=['_slot'])
    work['Horário']=work['_slot'].astype(int).map(lambda m:f'{m//60:02d}:{m%60:02d}')
    per_date=work.groupby(['Data','id','Atração','Horário'],as_index=False)['Fila (min)'].median()
    return per_date.groupby(['id','Atração','Horário'],as_index=False).agg(**{
        'Mediana (min)':('Fila (min)','median'),'Média (min)':('Fila (min)','mean'),
        'Dias observados':('Data','nunique')})

def date_comparison(df,dates,include_weekday_baseline=True):
    selected=daily_stats(df[df['Data'].isin(dates)]).copy()
    selected['Referência']=selected['Data'].astype(str)
    if not include_weekday_baseline or not dates:return selected
    weekly=weekday_stats(df)
    pieces=[selected]
    for d in dates:
        subset=weekly[weekly['weekday']==d.weekday()].copy()
        if subset.empty:continue
        subset['Data']=d
        subset['Referência']=f'Típico {DAYS[d.weekday()]} ({d:%d/%m})'
        subset['Média (min)']=subset['Média (min)']
        subset['Amostras']=subset['Dias observados']
        pieces.append(subset[['Data','id','Atração','Média (min)','Mediana (min)','Amostras','Referência']])
    return pd.concat(pieces,ignore_index=True)
