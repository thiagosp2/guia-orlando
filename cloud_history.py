"""Shared historical cache via server-side Supabase PostgREST.
Requires SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in Streamlit Secrets.
Never import this module into browser/client code or expose service key.
"""
import json
from datetime import date
import requests

TIMEOUT=15


def _config():
    try:
        import streamlit as st
        url=str(st.secrets.get('SUPABASE_URL','')).rstrip('/')
        key=str(st.secrets.get('SUPABASE_SERVICE_ROLE_KEY',''))
        if url.startswith('https://') and key:
            return url,key
    except (ImportError,FileNotFoundError,KeyError,RuntimeError):
        pass
    return None


def enabled():
    return _config() is not None


def _headers(key):
    return {'apikey':key,'Authorization':'Bearer '+key,'Content-Type':'application/json'}


def read(park,days,ttl_seconds=86400*30):
    """Return valid rows, never fabricate missing data; raise on cloud errors."""
    from time import time
    config=_config()
    if not config or not days:return {}
    url,key=config
    result={}
    # 30 dates fit within a single PostgREST IN filter; chunk larger inputs.
    lookup={d.isoformat():d for d in days}
    dates=list(lookup)
    for offset in range(0,len(dates),80):
        chunk=dates[offset:offset+80]
        r=requests.get(url+'/rest/v1/shared_history_cache',params={
            'select':'day,payload,saved_at', 'park':'eq.'+park,
            'day':'in.('+','.join(chunk)+')'},headers=_headers(key),timeout=TIMEOUT)
        r.raise_for_status()
        for row in r.json():
            if row['day'] in lookup and time()-int(row['saved_at'])<ttl_seconds:
                payload=row['payload']
                if isinstance(payload,(dict,list)):
                    result[lookup[row['day']]]=payload
    return result


def write(park,payloads):
    config=_config()
    if not config or not payloads:return False
    from time import time
    url,key=config
    rows=[{'park':park,'day':d.isoformat(),'payload':p,'saved_at':int(time())}
          for d,p in payloads.items()]
    for i in range(0,len(rows),50):
        r=requests.post(url+'/rest/v1/shared_history_cache',
            headers={**_headers(key),'Prefer':'resolution=merge-duplicates,return=minimal'},
            json=rows[i:i+50],timeout=TIMEOUT)
        r.raise_for_status()
    return True
