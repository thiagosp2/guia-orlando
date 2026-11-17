"""Mapa SVG com base cartográfica OpenStreetMap opcional e fallback offline.

Não requer Folium nem CDN de JavaScript; o navegador utiliza JavaScript nativo para zoom.
"""
import base64
import concurrent.futures
import html
import math
import os
from pathlib import Path
import time
import requests

TILE_CACHE = Path(__file__).parent / '.map_tiles'
TILE_URL = 'https://tile.openstreetmap.org/{z}/{x}/{y}.png'
TILE_TTL = 7 * 86400


def valid_point(lat, lon):
    try:
        a, b = float(lat), float(lon)
        return math.isfinite(a) and math.isfinite(b) and -90 <= a <= 90 and -180 <= b <= 180 and (a != 0 or b != 0)
    except (ValueError, TypeError):
        return False


def _world(lat, lon, zoom):
    lat = max(-85.0511, min(85.0511, float(lat)))
    scale = 256 * (2 ** zoom)
    latrad = math.radians(lat)
    return ((float(lon) + 180) / 360 * scale,
            (1 - math.asinh(math.tan(latrad)) / math.pi) / 2 * scale)


def _tile(z, x, y):
    if x < 0 or y < 0 or x >= 2 ** z or y >= 2 ** z:
        return None
    path = TILE_CACHE / str(z) / str(x) / f'{y}.png'
    try:
        if path.is_file() and time.time() - path.stat().st_mtime < TILE_TTL:
            return path.read_bytes()
        response = requests.get(TILE_URL.format(z=z, x=x, y=y), timeout=2.5,
                                headers={'User-Agent': 'GuiaOrlando/44 (personal theme-park trip planner; OSM attribution)'})
        response.raise_for_status()
        data = response.content
        if response.headers.get('Content-Type', '').startswith('image/png') and len(data) > 100:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            return data
    except (requests.RequestException, OSError):
        pass
    # Preserve stale tiles during connectivity outages.
    try:
        if path.is_file():
            return path.read_bytes()
    except OSError:
        pass
    return None


def make_park_map(locations, start_id=None, dest_id=None, route_points=None, fetch_tiles=True):
    """Render attractions and verified route over real OSM tiles, or schematic fallback.

    Tile fetching can be disabled for deterministic tests and offline operation.
    """
    points = [p for p in locations if valid_point(p.get('lat'), p.get('lon'))]
    if not points:
        return None
    route = [(float(a), float(b)) for a, b in (route_points or []) if valid_point(a, b)]
    coords = [(float(p['lat']), float(p['lon'])) for p in points] + route
    # Leave margin for attraction names and area labels.
    zoom = 12
    for z in range(18, 11, -1):
        world = [_world(a, b, z) for a, b in coords]
        if max(x for x, y in world) - min(x for x, y in world) <= 790 and max(y for x, y in world) - min(y for x, y in world) <= 395:
            zoom = z
            break
    world = [_world(a, b, zoom) for a, b in coords]
    center_x = (min(x for x, y in world) + max(x for x, y in world)) / 2
    center_y = (min(y for x, y in world) + max(y for x, y in world)) / 2
    def xy(lat, lon):
        x, y = _world(lat, lon, zoom)
        return round(480 + x - center_x, 2), round(285 + y - center_y, 2)

    # O fundo de segurança fica SEMPRE abaixo dos mosaicos. Falhas de rede
    # nunca produzem um quadrado branco ou escondem as atrações.
    shapes = ['<rect width="960" height="570" fill="#dcece0"/>',
              '<path d="M 25 420 Q 250 230 450 370 T 940 175" fill="none" stroke="#f7f5e9" stroke-width="34" opacity=".85"/>',
              '<path d="M 80 90 Q 330 210 580 100 T 930 310" fill="none" stroke="#f7f5e9" stroke-width="23" opacity=".85"/>']
    tiles = []
    x0, x1 = math.floor((center_x - 480) / 256), math.floor((center_x + 480) / 256)
    y0, y1 = math.floor((center_y - 285) / 256), math.floor((center_y + 285) / 256)
    keys = [(zoom, x, y) for x in range(x0, x1 + 1) for y in range(y0, y1 + 1)]
    if fetch_tiles:
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            tiles = list(pool.map(lambda key: _tile(*key), keys))
    loaded = 0
    for (z, tx, ty), data in zip(keys, tiles):
        if data:
            px = round(480 + tx * 256 - center_x, 2)
            py = round(285 + ty * 256 - center_y, 2)
            encoded = base64.b64encode(data).decode('ascii')
            shapes.append(f'<image x="{px}" y="{py}" width="256" height="256" href="data:image/png;base64,{encoded}"/>')
            loaded += 1
    # Se o Python não alcança os mosaicos (proxy/certificado), o navegador
    # tenta carregá-los diretamente. Cada tile falho fica transparente e
    # revela o fundo de segurança, sem apagar rótulos ou marcadores.
    if not loaded:
        for z, tx, ty in keys:
            px = round(480 + tx * 256 - center_x, 2)
            py = round(285 + ty * 256 - center_y, 2)
            url = html.escape(TILE_URL.format(z=z, x=tx, y=ty), quote=True)
            shapes.append(f'<image class="remote-tile" x="{px}" y="{py}" width="256" height="256" href="{url}"/>')
        shapes.append('<text x="480" y="35" text-anchor="middle" font-size="13" fill="#345943" class="offline-label">Se as ruas não aparecerem, verifique o acesso ao OpenStreetMap</text>')
    areas = {}
    for p in points:
        area = str(p.get('area') or '').strip()
        if area and area.casefold() not in ('nan', 'none', 'área não mapeada', 'não informada', 'desconhecida'):
            areas.setdefault(area, []).append((float(p['lat']), float(p['lon'])))
    for area, locs in areas.items():
        x, y = xy(sum(a for a, b in locs) / len(locs), sum(b for a, b in locs) / len(locs))
        label = html.escape(area)
        shapes.append(f'<text x="{x}" y="{max(65,y-22)}" text-anchor="middle" font-size="15" font-weight="bold" fill="#17354a" stroke="white" stroke-width="5" paint-order="stroke">{label}</text>')
    if len(route) >= 2:
        path = ' '.join(('M' if i == 0 else 'L') + f'{xy(a,b)[0]},{xy(a,b)[1]}' for i, (a,b) in enumerate(route))
        shapes.append(f'<path d="{path}" fill="none" stroke="white" stroke-width="9" stroke-linejoin="round"/>')
        shapes.append(f'<path d="{path}" fill="none" stroke="#0875cf" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"><title>Rota de caminhada verificada</title></path>')
    for p in points:
        lat, lon = float(p['lat']), float(p['lon'])
        x, y = xy(lat, lon)
        rid = str(p.get('id'))
        color = '#13864c' if rid == str(start_id) else '#d94c45' if rid == str(dest_id) else '#3d65b7'
        name = html.escape(str(p.get('name', 'Atração')))
        area = html.escape(str(p.get('area') or 'Área não identificada'))
        shapes.append(f'<circle cx="{x}" cy="{y}" r="7" fill="{color}" stroke="white" stroke-width="2"><title>{name} — {area} — {lat:.6f}, {lon:.6f}</title></circle>')
    note = '© OpenStreetMap contributors — openstreetmap.org/copyright · Base alternativa quando os mosaicos falharem'
    shapes.append(f'<rect x="8" y="541" width="944" height="25" fill="white" opacity=".88"/>')
    shapes.append(f'<text x="18" y="558" font-size="12" fill="#273e49">{html.escape(note)}</text>')
    # Interactive SVG viewport: browser-native pointer gestures, no Folium/CDN.
    controls = """<div class="map-controls" aria-label="Controles do mapa">
      <button type="button" id="zoom-in" title="Ampliar mapa" aria-label="Ampliar mapa">+</button>
      <button type="button" id="zoom-out" title="Reduzir mapa" aria-label="Reduzir mapa">−</button>
      <button type="button" id="zoom-reset" title="Restaurar visualização" aria-label="Restaurar visualização">⤢</button>
    </div>"""
    behavior = """<script>
    (function(){
      const svg = document.getElementById('park-map');
      const W=960, H=570, minScale=1, maxScale=12;
      let scale=1, cx=W/2, cy=H/2, dragging=false, lastX=0, lastY=0;
      function clamp(){
        const w=W/scale, h=H/scale;
        cx=Math.max(w/2,Math.min(W-w/2,cx));
        cy=Math.max(h/2,Math.min(H-h/2,cy));
      }
      function render(){
        clamp();
        const w=W/scale,h=H/scale;
        svg.setAttribute('viewBox',`${cx-w/2} ${cy-h/2} ${w} ${h}`);
      }
      function coords(event){
        const r=svg.getBoundingClientRect();
        return [(event.clientX-r.left)/r.width,(event.clientY-r.top)/r.height];
      }
      function zoom(factor, px=.5, py=.5){
        const oldW=W/scale,oldH=H/scale;
        const ax=cx+(px-.5)*oldW, ay=cy+(py-.5)*oldH;
        scale=Math.max(minScale,Math.min(maxScale,scale*factor));
        const newW=W/scale,newH=H/scale;
        cx=ax-(px-.5)*newW; cy=ay-(py-.5)*newH;
        render();
      }
      document.getElementById('zoom-in').addEventListener('click',()=>zoom(1.5));
      document.getElementById('zoom-out').addEventListener('click',()=>zoom(1/1.5));
      document.getElementById('zoom-reset').addEventListener('click',()=>{scale=1;cx=W/2;cy=H/2;render();});
      svg.addEventListener('wheel', e=>{
        e.preventDefault();
        const [x,y]=coords(e);zoom(e.deltaY<0?1.25:1/1.25,x,y);
      },{passive:false});
      svg.addEventListener('pointerdown',e=>{
        if(e.button!==0) return;
        dragging=true;lastX=e.clientX;lastY=e.clientY;
        svg.setPointerCapture(e.pointerId);
      });
      svg.addEventListener('pointermove',e=>{
        if(!dragging) return;
        const r=svg.getBoundingClientRect();
        cx-=(e.clientX-lastX)*(W/scale)/r.width;
        cy-=(e.clientY-lastY)*(H/scale)/r.height;
        lastX=e.clientX;lastY=e.clientY;render();
      });
      function endDrag(){dragging=false;}
      svg.addEventListener('pointerup',endDrag);
      svg.addEventListener('pointercancel',endDrag);
      svg.addEventListener('lostpointercapture',endDrag);
      svg.addEventListener('dblclick',e=>{
        e.preventDefault();const [x,y]=coords(e);zoom(1.5,x,y);
      });
      // Não deixar mosaicos quebrados ocultarem o fundo alternativo.
      document.querySelectorAll('.remote-tile').forEach(tile => {
        tile.addEventListener('error', () => tile.remove());
        tile.addEventListener('load', () => {
          const label=document.querySelector('.offline-label');
          if(label) label.remove();
        });
      });
      render();
    })();
    </script>"""
    css = """<style>
      html,body{margin:0;padding:0;background:#e8f0e9;font-family:Arial,sans-serif;overflow:hidden}
      .map-shell{position:relative;width:100%;height:570px;overflow:hidden}
      #park-map{width:100%;height:100%;display:block;cursor:grab;touch-action:none;user-select:none}
      #park-map:active{cursor:grabbing}
      .map-controls{position:absolute;z-index:2;top:12px;right:12px;display:flex;flex-direction:column;gap:4px}
      .map-controls button{width:39px;height:39px;background:#fff;border:1px solid #aebbc2;
        border-radius:6px;box-shadow:0 1px 5px #0003;color:#17354a;font-size:23px;
        font-weight:bold;cursor:pointer}
      .map-controls button:hover{background:#edf3f8}
    </style>"""
    return ('<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">'+css+'</head><body>'
            '<div class="map-shell">'+controls+
            '<svg id="park-map" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 570" '
            'role="img" aria-label="Mapa interativo de atrações, áreas e rota de caminhada">'
            + ''.join(shapes) + '</svg></div>'+behavior+'</body></html>')
