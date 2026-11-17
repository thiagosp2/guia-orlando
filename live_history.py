"""Convert verified ThemeParks.wiki historical park-days into opportunity observations.
No synthetic queues; returns diagnostics when historical coverage is unavailable.
"""
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from period_history import period_waits
from planner_cache import collect_history

ORLANDO=ZoneInfo('America/New_York')

def historical_opportunity_samples(park_id, request_one, today=None, days=30, db=None):
    today=today or datetime.now(ORLANDO).date()
    dates=[today-timedelta(days=i) for i in range(1,days+1)]
    opts={'max_workers':6,'retry_count':1}
    if db is not None: opts['db']=db
    payloads, errors, stats=collect_history([park_id], dates, request_one, **opts)
    found=payloads.get(park_id,{})
    if not found:
        return [],errors,stats
    frame=period_waits(found, start_hour=9,end_hour=22,step_minutes=30,max_days=days)
    samples=[]
    for item in frame.itertuples(index=False):
        day=item[0]; rid=item[2]; hour=item[4]; wait=item[5]
        local=datetime.fromisoformat(f'{day.isoformat()}T{hour}:00').replace(tzinfo=ORLANDO)
        samples.append((str(rid),local.astimezone(timezone.utc).isoformat(),float(wait)))
    stats={**stats,'park_days':len(found),'valid_samples':len(samples),'rides':len(set(x[0] for x in samples))}
    return samples,errors,stats
