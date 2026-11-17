"""Save only UI search parameters, not results, credentials or API payloads."""
import json
import os
import sqlite3
import cloud_accounts
from datetime import date, datetime
from pathlib import Path

DB = Path(__file__).with_name('saved_views.sqlite3')
KEYS = {'park_all','regular_only','planned_start','planned_end','planned_custom_enabled','planned_parks','planned_first','planned_last','analysis_park','analysis_rides','analysis_days','analysis_mode','v30_daily_metric','v30_week_metric','v30_week_min','v30_hour_weekday','v30_hour_range','v30_hour_metric','v47_ranking_start','v47_ranking_end','v47_ranking_parks'}
PREFIXES = ('planned_rides_','must_select_','p_','d_','route_start_','route_dest_','planned_custom_date_')
def allowed(k):
    return k in KEYS or k.startswith(PREFIXES)
def serialize(v):
    if isinstance(v,(date,datetime)): return {'date':v.isoformat()}
    if isinstance(v,tuple): return list(v)
    if isinstance(v,(str,int,float,bool,list)) or v is None: return v
    raise TypeError('unsupported')
def deserialize(v):
    if isinstance(v,dict) and 'date' in v: return date.fromisoformat(v['date'])
    return v
def connect():
    db=sqlite3.connect(DB,timeout=10)
    db.execute('CREATE TABLE IF NOT EXISTS params (key TEXT PRIMARY KEY, value TEXT NOT NULL)')
    return db
def restore(state):
    if os.environ.get("ORLANDO_PUBLIC_MODE", "0") == "1":
        cloud_accounts.load(state,allowed,deserialize)
        return
    try:
        with connect() as db:
            for key,value in db.execute('SELECT key,value FROM params'):
                if allowed(key) and key not in state:
                    try: state[key]=deserialize(json.loads(value))
                    except (ValueError,TypeError): pass
    except sqlite3.Error: pass
def save(state):
    if os.environ.get("ORLANDO_PUBLIC_MODE", "0") == "1":
        cloud_accounts.save(state,allowed,serialize)
        return
    rows=[]
    for key in list(state):
        if allowed(key):
            try: rows.append((key,json.dumps(serialize(state[key]),ensure_ascii=False)))
            except (ValueError,TypeError): pass
    if rows:
        try:
            with connect() as db:
                db.executemany('INSERT OR REPLACE INTO params VALUES (?,?)',rows)
        except sqlite3.Error: pass
def clear(state):
    if os.environ.get("ORLANDO_PUBLIC_MODE", "0") == "1":
        cloud_accounts.clear(state,allowed)
        for key in list(state):
            if allowed(key): del state[key]
        return
    try:
        with connect() as db: db.execute('DELETE FROM params')
    except sqlite3.Error: pass
    for key in list(state):
        if allowed(key): del state[key]
