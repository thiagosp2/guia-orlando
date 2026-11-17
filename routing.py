"""Pedestrian routing via a public Valhalla demo endpoint or a custom endpoint.
Demo servers are best-effort and may be unavailable or rate limited.
"""
import json
import sqlite3
import time
from pathlib import Path

import requests
import ssl
try:
    import truststore
except ImportError:
    truststore = None  # Use Python default certificate store when unavailable.
from requests.adapters import HTTPAdapter

PUBLIC_VALHALLA = "https://valhalla1.openstreetmap.de"

class WindowsTrustAdapter(HTTPAdapter):
    def init_poolmanager(self, connections, maxsize, block=False, **kwargs):
        kwargs["ssl_context"] = (truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT) if truststore else ssl.create_default_context())
        return super().init_poolmanager(connections, maxsize, block=block, **kwargs)

DB = Path(__file__).parent / 'walking_routes.sqlite3'


def init_db():
    with sqlite3.connect(DB) as con:
        con.execute("""CREATE TABLE IF NOT EXISTS routes (
            park TEXT NOT NULL, origin TEXT NOT NULL, destination TEXT NOT NULL,
            distance_m REAL NOT NULL, duration_min REAL NOT NULL,
            geometry TEXT NOT NULL, fetched_at INTEGER NOT NULL,
            PRIMARY KEY (park,origin,destination))""")


def cached(park, origin, destination, max_age_days=30):
    init_db()
    with sqlite3.connect(DB) as con:
        row = con.execute('SELECT distance_m,duration_min,geometry,fetched_at FROM routes WHERE park=? AND origin=? AND destination=?',
                          (park,str(origin),str(destination))).fetchone()
    if row and time.time()-row[3] < max_age_days*86400:
        return {'distance_m':row[0], 'duration_min':row[1], 'points':json.loads(row[2]), 'source':'Valhalla (cache)'}
    return None


def fetch_route(base_url, park, origin, destination, start, finish, speed_kmh=4.0):
    """Return actual pedestrian route only if a configured service returns valid coordinates.
    Valhalla returns a route duration based on its own model; scale by distance/user speed.
    """
    old=cached(park,origin,destination)
    if old:
        return {**old,'duration_min':round(old['distance_m']/1000/speed_kmh*60,1)}
    if not base_url.strip():
        return None
    url=base_url.rstrip('/')+'/route'
    params={'locations':[{'lat':float(start[0]),'lon':float(start[1])},
                          {'lat':float(finish[0]),'lon':float(finish[1])}],
            'costing':'pedestrian','directions_options':{'units':'kilometers'}}
    # Send Valhalla request as JSON POST body, avoiding URL JSON parsing issues.
    # SSL uses the Windows trust store, including trusted corporate roots.
    with requests.Session() as session:
        session.mount('https://', WindowsTrustAdapter())
        response=session.post(url, json=params, headers={'Accept':'application/json'}, timeout=25)
        if not response.ok:
            try:
                detail = response.json()
                message = detail.get('error') or detail.get('error_message') or detail.get('message') or str(detail)
                code = detail.get('error_code', detail.get('status_code', ''))
            except ValueError:
                message = response.text[:350]
                code = ''
            raise ValueError(f"Valhalla HTTP {response.status_code} (código {code}): {str(message)[:400]}")
        payload=response.json()
    trip=payload['trip']
    length_km=float(trip['summary']['length'])
    if not 0 < length_km < 20: raise ValueError('Distância de rota inesperada')
    legs=trip.get('legs') or []
    shape=legs[0].get('shape') if legs else None
    points=decode_polyline6(shape) if shape else []
    if len(points)<2: raise ValueError('Rota sem geometria válida')
    distance=length_km*1000
    duration=round(length_km/speed_kmh*60,1)
    init_db()
    with sqlite3.connect(DB) as con:
        con.execute('INSERT OR REPLACE INTO routes VALUES (?,?,?,?,?,?,?)',
                    (park,str(origin),str(destination),distance,duration,json.dumps(points),int(time.time())))
    return {'distance_m':distance,'duration_min':duration,'points':points,'source':'Valhalla (rota OSM)'}


def decode_polyline6(encoded):
    """Decode Valhalla encoded polyline (precision 1e-6) to [lat, lon] pairs."""
    coordinates=[]; index=0; lat=lon=0
    while index<len(encoded):
        values=[]
        for _ in range(2):
            shift=0; result=0
            while True:
                if index>=len(encoded): raise ValueError('Polyline truncada')
                b=ord(encoded[index])-63; index+=1
                result|=(b & 0x1f)<<shift
                shift+=5
                if b<0x20: break
            values.append(~(result>>1) if result&1 else result>>1)
        lat+=values[0]; lon+=values[1]
        coordinates.append([lat/1e6,lon/1e6])
    return coordinates
