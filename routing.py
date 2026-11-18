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

DB = Path(__file__).parent / 'walking_routes_v61.sqlite3'
# Novo cache: descarta estimativas antigas calculadas em apenas um sentido.


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
    """Compare os dois sentidos da malha de pedestres e escolha o menor trajeto válido.

    Alguns caminhos do OSM nos parques possuem sentido único cadastrado
    incorretamente. A rota inversa é invertida geometricamente para continuar
    sendo exibida da origem solicitada ao destino solicitado.
    """
    if speed_kmh <= 0:
        raise ValueError('Velocidade de caminhada inválida')
    old = cached(park, origin, destination)
    if old:
        return {**old, 'duration_min': round(old['distance_m']/1000/speed_kmh*60, 1)}
    if not base_url.strip():
        return None

    url = base_url.rstrip('/') + '/route'
    candidates = []
    errors = []
    with requests.Session() as session:
        session.mount('https://', WindowsTrustAdapter())
        for first, last, reverse in ((start, finish, False), (finish, start, True)):
            params = {
                'locations': [{'lat': float(first[0]), 'lon': float(first[1])},
                              {'lat': float(last[0]), 'lon': float(last[1])}],
                'costing': 'pedestrian',
                'directions_options': {'units': 'kilometers'},
            }
            try:
                response = session.post(url, json=params,
                                        headers={'Accept': 'application/json'}, timeout=25)
                response.raise_for_status()
                trip = response.json()['trip']
                length_km = float(trip['summary']['length'])
                if not 0 < length_km < 20:
                    raise ValueError('Distância de rota inesperada')
                legs = trip.get('legs') or []
                points = []
                for leg in legs:
                    if leg.get('shape'):
                        segment = decode_polyline6(leg['shape'])
                        points.extend(segment if not points else segment[1:])
                if len(points) < 2:
                    raise ValueError('Rota sem geometria válida')
                if reverse:
                    points.reverse()
                candidates.append((length_km * 1000, points, reverse))
            except (requests.RequestException, ValueError, KeyError, TypeError, IndexError) as exc:
                errors.append(str(exc))

    if not candidates:
        raise ValueError('Nenhuma rota de pedestres válida nos dois sentidos: ' + '; '.join(errors)[:300])
    distance, points, used_reverse = min(candidates, key=lambda item: item[0])
    duration = round(distance/1000/speed_kmh*60, 1)
    init_db()
    with sqlite3.connect(DB) as con:
        con.execute('INSERT OR REPLACE INTO routes VALUES (?,?,?,?,?,?,?)',
                    (park, str(origin), str(destination), distance, duration,
                     json.dumps(points), int(time.time())))
    return {'distance_m': distance, 'duration_min': duration, 'points': points,
            'source': 'Valhalla (menor rota nos dois sentidos' +
                      (', sentido inverso' if used_reverse else '') + ')'}


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
