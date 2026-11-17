"""Bounded, persistent history retrieval for the trip planner.
Only successful API responses are cached; failed dates remain missing.
"""
import json
import random
import sqlite3
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path

import requests
import cloud_history

CACHE_DB = Path(__file__).parent / "planner_history_cache.sqlite3"


def _connect(db):
    conn = sqlite3.connect(db, timeout=8)
    conn.execute("PRAGMA busy_timeout=8000")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""CREATE TABLE IF NOT EXISTS history_cache (
        park TEXT NOT NULL, day TEXT NOT NULL, payload TEXT NOT NULL,
        saved_at INTEGER NOT NULL, PRIMARY KEY (park, day))""")
    return conn


def read_cached(park, days, db=CACHE_DB, ttl_seconds=86400 * 30):
    """Fetch immutable past-day snapshots; do not reuse stale entries indefinitely."""
    if not days:
        return {}
    try:
        with _connect(db) as conn:
            rows=conn.execute("SELECT day,payload,saved_at FROM history_cache WHERE park=?",(park,)).fetchall()
    except (sqlite3.Error, OSError):
        return {}
    allowed={d.isoformat():d for d in days}
    now=time.time()
    result={}
    for day_str, raw, saved_at in rows:
        if day_str in allowed and now-saved_at < ttl_seconds:
            try:
                result[allowed[day_str]]=json.loads(raw)
            except (ValueError,TypeError):
                pass
    return result


def write_cached(park, payloads, db=CACHE_DB):
    if not payloads:
        return False
    try:
        with _connect(db) as conn:
            conn.executemany("INSERT OR REPLACE INTO history_cache VALUES (?,?,?,?)",
                [(park, day.isoformat(), json.dumps(payload), int(time.time()))
                 for day,payload in payloads.items()])
        return True
    except (sqlite3.Error, OSError, TypeError, ValueError):
        return False


def collect_history(parks, days, request_one, db=CACHE_DB, max_workers=3,
                    progress=None, retry_count=2, sleep=time.sleep):
    """Retrieve only cache misses with bounded concurrency and 429/5xx backoff.

    request_one(park_id, day) must be thread-safe and must not access Streamlit.
    Progress callback runs on the calling thread. Returns (by_park, errors, metrics).
    """
    if not 1 <= max_workers <= 6:
        raise ValueError('max_workers must be between 1 and 6')
    days=list(days)
    by_park={}; tasks=[]; cache_hits=0; cloud_hits=0; cloud_errors=[]
    for park_id in parks:
        cached=read_cached(park_id,days,db=db)
        missing=[d for d in days if d not in cached]
        if missing and cloud_history.enabled():
            try:
                remote=cloud_history.read(park_id,missing)
                cached.update(remote)
                cloud_hits+=len(remote)
                write_cached(park_id,remote,db=db)
            except (requests.RequestException,ValueError,KeyError,TypeError) as exc:
                cloud_errors.append(f'{park_id}: {str(exc)[:140]}')
        by_park[park_id]=cached
        cache_hits+=len(cached)
        tasks.extend((park_id,d) for d in days if d not in cached)
    total=len(tasks)
    done=0; failures=[]; new_payloads={p:{} for p in parks}
    def fetch(task):
        park_id,day=task
        for attempt in range(retry_count+1):
            try:
                return request_one(park_id,day)
            except (requests.RequestException,RuntimeError,ValueError) as exc:
                message=str(exc)
                retryable=('429' in message or '500' in message or '502' in message
                           or '503' in message or '504' in message
                           or isinstance(exc,(requests.Timeout,requests.ConnectionError)))
                if not retryable or attempt==retry_count:
                    raise
                sleep(min(8, 1.5*(2**attempt)))
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        future_map={pool.submit(fetch,task):task for task in tasks}
        for future in as_completed(future_map):
            park_id,day=future_map[future]
            try:
                payload=future.result()
                if not isinstance(payload,(dict,list)):
                    raise ValueError('Resposta histórica inválida')
                by_park[park_id][day]=payload
                new_payloads[park_id][day]=payload
            except (requests.RequestException,RuntimeError,ValueError,TypeError) as exc:
                failures.append(f'{park_id} {day:%d/%m}: {str(exc)[:110]}')
            done+=1
            if progress:
                progress(done,total)
    persisted=sum(len(x) for x in new_payloads.values())
    for park_id,payloads in new_payloads.items():
        write_cached(park_id,payloads,db=db)
        if payloads and cloud_history.enabled():
            try: cloud_history.write(park_id,payloads)
            except (requests.RequestException,ValueError,KeyError,TypeError) as exc:
                cloud_errors.append(f'{park_id}: {str(exc)[:140]}')
    return by_park,failures,{'cache_hits':cache_hits,'api_requests':total,
        'successful_requests':persisted,'failed_requests':len(failures),
        'cloud_hits':cloud_hits,'cloud_errors':cloud_errors}
