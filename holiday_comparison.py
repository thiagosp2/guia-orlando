"""Comparação transparente entre feriados passados e previsão futura.

Nunca gera fator de feriado sem observações reais de feriados anteriores.
As médias são de filas ANUNCIADAS, não tempos efetivamente experimentados.
"""
from datetime import date, timedelta
import pandas as pd
from holiday_model import thanksgiving, clean_daily


def _normalize_park_days(df):
    """Aceita CSV diário por atração (Chart the Magic) ou parque-dia (fontes externas)."""
    d=df.copy()
    if 'avg_posted_wait_min' not in d and 'average_wait_min' in d:
        d=d.rename(columns={'average_wait_min':'avg_posted_wait_min'})
    needed={'date','park','avg_posted_wait_min'}
    if not needed.issubset(d):
        raise ValueError('CSV precisa conter date, park e avg_posted_wait_min (ou average_wait_min).')
    d['date']=pd.to_datetime(d['date'],errors='coerce').dt.date
    d['avg_posted_wait_min']=pd.to_numeric(d['avg_posted_wait_min'],errors='coerce')
    d=d[d['date'].notna() & d['avg_posted_wait_min'].between(0,600)].copy()
    d['park']=d['park'].astype(str).str.strip()
    if 'ride' in d:
        d['ride']=d['ride'].astype(str).str.strip()
        if 'readings' in d:
            d['readings']=pd.to_numeric(d['readings'],errors='coerce')
            d=d[d['readings']>=3]
        d=d.drop_duplicates(['date','park','ride'])
        d=d.groupby(['date','park'],as_index=False)['avg_posted_wait_min'].mean()
    else:
        d=d.groupby(['date','park'],as_index=False)['avg_posted_wait_min'].mean()
    return d


def compare_holiday_years(df, park, target, minimum_years=2):
    """Usa Thanksgiving +/- dias; baseline em semanas adjacentes no MESMO ano.

    Normaliza por ano (razão feriado / referência), evitando comparar diretamente
    anos com diferentes níveis de filas. Sem >=minimum_years, não projeta.
    """
    data=_normalize_park_days(df)
    data=data[data.park.str.casefold()==park.casefold()].copy()
    if data.empty:
        return pd.DataFrame(), None
    target_offset=(target-thanksgiving(target.year)).days
    rows=[]
    for year in sorted({d.year for d in data.date if d.year<target.year}):
        holiday=thanksgiving(year)+timedelta(days=target_offset)
        observed=data.loc[data.date==holiday,'avg_posted_wait_min']
        # Duas semanas antes/depois, mesmos dias da semana, sem dias da semana do Thanksgiving.
        reference_days=[holiday+timedelta(days=k) for k in (-21,-14,-7,7,14,21)]
        reference_days=[d for d in reference_days if abs((d-thanksgiving(year)).days)>6]
        baseline=data[data.date.isin(reference_days)]['avg_posted_wait_min']
        if observed.empty or len(baseline)<2:
            rows.append({'Ano':year,'Data feriado':holiday,'Fila real feriado (min)':float(observed.iloc[0]) if not observed.empty else None,
                         'Fila normal (min)':None,'Diferença (%)':None,'Dias referência':len(baseline),
                         'Comparável':False})
            continue
        base=float(baseline.median()); actual=float(observed.iloc[0])
        rows.append({'Ano':year,'Data feriado':holiday,'Fila real feriado (min)':round(actual,1),
                     'Fila normal (min)':round(base,1),'Diferença (%)':round(100*(actual/base-1),1) if base>0 else None,
                     'Dias referência':len(baseline),'Comparável':base>0})
    history=pd.DataFrame(rows,columns=['Ano','Data feriado','Fila real feriado (min)','Fila normal (min)',
                                       'Diferença (%)','Dias referência','Comparável'])
    if history.empty:return history,None
    valid=history[history['Comparável'] & history['Diferença (%)'].notna()].copy()
    if len(valid)<minimum_years:return history,None
    # Referência futura: datas próximas anteriores ao alvo, mesmo dia da semana,
    # excluindo semana de Thanksgiving; no máximo 8 semanas.
    candidate=[target-timedelta(days=7*k) for k in range(1,9)]
    candidate=[d for d in candidate if abs((d-thanksgiving(d.year)).days)>6]
    baseline=data[data.date.isin(candidate)]['avg_posted_wait_min']
    if len(baseline)<2:return history,None
    baseline_value=float(baseline.median())
    factor=float(valid['Diferença (%)'].median())/100
    ratios=valid['Diferença (%)'].astype(float).sort_values()/100
    lower=float(ratios.quantile(.2)); upper=float(ratios.quantile(.8))
    result={'baseline':round(baseline_value,1),'predicted':round(max(0,baseline_value*(1+factor)),1),
            'low':round(max(0,baseline_value*(1+lower)),1),'high':round(max(0,baseline_value*(1+upper)),1),
            'effect_percent':round(100*factor,1),'years':len(valid),'reference_days':len(baseline),
            'method':'Mediana de razões anuais (feriado / dias normais do mesmo ano)'}
    return history,result
