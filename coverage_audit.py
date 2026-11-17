"""Auditoria da cobertura real de históricos gratuitos, sem imputação de filas."""
from datetime import date, timedelta
import pandas as pd

PARKS_DISNEY = ('Magic Kingdom','EPCOT','Hollywood Studios','Animal Kingdom')

def thanksgiving(year):
    first=date(year,11,1)
    first_thursday=first+timedelta(days=(3-first.weekday())%7)
    return first_thursday+timedelta(days=21)

def audit_coverage(frames, years=(2023,2024,2025), parks=PARKS_DISNEY):
    """Avalia presença de registros para Thanksgiving e seis datas de referência.
    Não presume que a média por atração equivale à média do parque inteiro.
    """
    columns=['Fonte','Parque','Ano','Thanksgiving','Dias normais (de 6)',
             'Atrações no feriado','Registros no feriado','Cobertura','Motivo']
    output=[]
    for frame in frames:
        if frame is None or frame.empty: continue
        d=frame.copy()
        if not {'date','park','avg_posted_wait_min'}.issubset(d.columns):continue
        d['date']=pd.to_datetime(d['date'],errors='coerce').dt.date
        d['avg_posted_wait_min']=pd.to_numeric(d['avg_posted_wait_min'],errors='coerce')
        d=d[d['date'].notna() & d['avg_posted_wait_min'].between(0,600)]
        if d.empty:continue
        d['park']=d['park'].astype(str).str.strip()
        if 'source' not in d:d['source']='Importação local'
        for source, group in d.groupby('source'):
            for park in parks:
                p=group[group.park.str.casefold()==park.casefold()]
                if p.empty:continue
                for year in years:
                    h=thanksgiving(year)
                    reference=[h+timedelta(days=n) for n in (-21,-14,-7,7,14,21)]
                    holiday=p[p.date==h]
                    baseline=p[p.date.isin(reference)]
                    days=baseline.date.nunique()
                    attractions=holiday.ride.nunique() if 'ride' in holiday else (1 if not holiday.empty else 0)
                    has_holiday=not holiday.empty
                    good=has_holiday and days>=2
                    if not has_holiday:reason='Sem observação no feriado'
                    elif days<2:reason='Menos de 2 dias normais de referência'
                    else:reason='Comparação básica possível; avaliar representatividade'
                    output.append({'Fonte':source,'Parque':park,'Ano':year,'Thanksgiving':h,
                                   'Dias normais (de 6)':days,'Atrações no feriado':attractions,
                                   'Registros no feriado':len(holiday),
                                   'Cobertura':'Comparável' if good else 'Insuficiente','Motivo':reason})
    return pd.DataFrame(output,columns=columns)

def coverage_summary(audit):
    if audit.empty:return {'comparaveis':0,'total':0,'anos':[]}
    valid=audit[audit.Cobertura=='Comparável']
    return {'comparaveis':len(valid),'total':len(audit),'anos':sorted(valid.Ano.unique().tolist())}
