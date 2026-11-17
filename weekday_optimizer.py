"""Best visit hours from observed local waits, by weekday (Orlando local time).

Avoids using holiday/event anomalies and never fabricates unsupported slots.
"""
from collections import defaultdict
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
import math
import statistics
import pandas as pd

TZ=ZoneInfo('America/New_York')
DAYS=['Segunda-feira','Terça-feira','Quarta-feira','Quinta-feira','Sexta-feira','Sábado','Domingo']

def holiday_window(year):
    """Major US holiday windows and observed federal holidays; conservative filter."""
    from pandas.tseries.holiday import USFederalHolidayCalendar
    start=pd.Timestamp(year=year,month=1,day=1)
    end=pd.Timestamp(year=year,month=12,day=31)
    federal=set(x.date() for x in USFederalHolidayCalendar().holidays(start=start,end=end))
    thanksgiving=date(year,11,1)
    thanksgiving+=timedelta(days=(3-thanksgiving.weekday())%7+21)
    special={thanksgiving+timedelta(days=i) for i in range(-3,4)}
    special|={date(year,12,25)+timedelta(days=i) for i in range(-4,7)}
    special|={date(year,1,1)+timedelta(days=i) for i in range(-2,3)}
    special|={date(year,7,4)+timedelta(days=i) for i in range(-2,3)}
    return federal|special

def best_hours(observations, ride_ids, weekday, start_hour=10, end_hour=18,
               min_days=3, now=None, excluded_dates=()):
    """Return per-ride hourly estimates using independent historical dates.

    Each hour uses daily median within ±30 minutes of its midpoint. A daily
    median anomaly filter removes entire park-wide atypical dates, then a
    per-ride/hour MAD filter removes isolated outliers. Only past samples.
    """
    now=now or datetime.now(TZ)
    if now.tzinfo is None: raise ValueError('now must be timezone-aware')
    now=now.astimezone(TZ)
    ids={str(x) for x in ride_ids}
    excluded=set(excluded_dates)
    data=[]
    for rid,timestamp,wait in observations:
        if str(rid) not in ids:continue
        try:
            t=datetime.fromisoformat(str(timestamp).replace('Z','+00:00')).astimezone(TZ)
            w=float(wait)
        except (ValueError,TypeError,OverflowError):continue
        if not math.isfinite(w) or not 0<=w<=600 or t>=now or t.weekday()!=weekday:continue
        if t.date() in excluded or t.date() in holiday_window(t.year):continue
        data.append((str(rid),t,w))
    # Park-wide atypical days: median daily waits across all observed attractions
    park_day=defaultdict(list)
    for _,t,w in data:park_day[t.date()].append(w)
    park_medians={d:statistics.median(ws) for d,ws in park_day.items() if len(ws)>=3}
    anomalous=set()
    if len(park_medians)>=6:
        med=statistics.median(park_medians.values())
        deviations=[abs(v-med) for v in park_medians.values()]
        mad=statistics.median(deviations)
        if mad>0:
            anomalous={d for d,v in park_medians.items() if abs(v-med)>3.5*1.4826*mad}
    slots=defaultdict(lambda:defaultdict(list))
    for rid,t,w in data:
        if t.date() in anomalous:continue
        for hour in range(start_hour,end_hour+1):
            if abs((t.hour*60+t.minute)-(hour*60))<=30:
                slots[(rid,hour)][t.date()].append(w)
    rows=[]
    for rid in ids:
        for hour in range(start_hour,end_hour+1):
            by_day=slots[(rid,hour)]
            values=[statistics.median(v) for v in by_day.values()]
            if len(values)>=5:
                median=statistics.median(values)
                mad=statistics.median(abs(v-median) for v in values)
                if mad>0:
                    values=[v for v in values if abs(v-median)<=3.5*1.4826*mad]
            if len(values)<min_days:continue
            rows.append({'id':rid,'Horário':f'{hour:02d}:00','Fila típica (min)':round(statistics.median(values)),
                         'Dias observados':len(values),'Mínimo típico (min)':round(min(values)),
                         'Máximo típico (min)':round(max(values))})
    result=pd.DataFrame(rows)
    if result.empty:return result
    result['Melhor horário']=False
    for rid,group in result.groupby('id'):
        idx=group.sort_values(['Fila típica (min)','Horário']).index[0]
        result.loc[idx,'Melhor horário']=True
    return result.sort_values(['id','Horário']).reset_index(drop=True)
