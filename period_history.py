"""Aggregations of observed hourly queues for a selected period of up to 7 days."""
from datetime import datetime, time, timedelta, timezone
import pandas as pd
from core import TZ, history_entities, state_at

WEEKDAYS_PT = ('segunda-feira','terça-feira','quarta-feira','quinta-feira','sexta-feira','sábado','domingo')

def period_waits(day_payloads, metadata=None, start_hour=10, end_hour=18, step_minutes=30, stale_minutes=90, max_days=7, ride_ids=None):
    if not 0 <= start_hour <= end_hour <= 23: raise ValueError('Horários inválidos')
    if step_minutes not in (15,30,60):raise ValueError('Intervalo inválido')
    if not 1 <= len(day_payloads) <= max_days:raise ValueError(f'Selecione entre 1 e {max_days} dias')
    metadata=metadata or {}
    allowed = None if ride_ids is None else {str(r) for r in ride_ids}
    rows=[]
    for day,payload in sorted(day_payloads.items()):
        if not isinstance(payload,dict):continue
        for rid,entity in history_entities(payload):
            if not rid or (allowed is not None and str(rid) not in allowed):continue
            name=(entity.get('name') or (entity.get('entity') or {}).get('name') or metadata.get(rid,{}).get('name') or rid)
            for minute in range(start_hour*60,end_hour*60+1,step_minutes):
                local=datetime.combine(day,time(minute//60,minute%60),TZ)
                state=state_at(entity,local.astimezone(timezone.utc),stale_minutes)
                if state['status']!='OPERATING' or state['wait'] is None:continue
                rows.append({'Data':day,'Dia da semana':WEEKDAYS_PT[day.weekday()], 'id':rid,
                             'Atração':name,'Horário':local.strftime('%H:%M'),'Fila (min)':float(state['wait'])})
    return pd.DataFrame(rows,columns=['Data','Dia da semana','id','Atração','Horário','Fila (min)'])

def summarize_period(observations):
    if observations.empty:
        return pd.DataFrame(),pd.DataFrame(),pd.DataFrame()
    # Each attraction contributes equally to a park-day mean, regardless of observation count.
    rides=observations.groupby(['Data','Dia da semana','id','Atração'],as_index=False).agg(
        **{'Fila média (min)':('Fila (min)','mean'), 'Amostras':('Fila (min)','size')})
    rides['Fila média (min)']=rides['Fila média (min)'].round(1)
    days=rides.groupby(['Data','Dia da semana'],as_index=False).agg(
        **{'Fila média do parque (min)':('Fila média (min)','mean'), 'Atrações observadas':('id','nunique'),
           'Amostras':('Amostras','sum')})
    days['Fila média do parque (min)']=days['Fila média do parque (min)'].round(1)
    overall=rides.groupby(['id','Atração'],as_index=False).agg(
        **{'Fila média no período (min)':('Fila média (min)','mean'), 'Dias com dados':('Data','nunique'),
           'Amostras':('Amostras','sum')})
    overall['Fila média no período (min)']=overall['Fila média no período (min)'].round(1)
    return days,rides,overall
