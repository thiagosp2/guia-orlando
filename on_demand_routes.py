"""Resolve only walking legs that the itinerary optimizer actually proposes.

Routes are directional and fetched through routing.fetch_route, which owns the
persistent SQLite cache. Unavailable routes remain unknown, never zero-minute.
"""
from concurrent.futures import ThreadPoolExecutor
import math


def optimize_on_demand(profile, selected, catalog, day, park, coords, fetch,
                       optimizer, buffer_min=20, ride_duration_min=12,
                       max_workers=3, attempted=None, matrix=None):
    """Iteratively refine a proposed itinerary with verified pedestrian legs.

    A failed pair is attempted once per planning run. There is no fixed number
    of attraction pairs: only consecutive legs in candidate itineraries are
    requested. Cached results can be passed in from another itinerary option.
    """
    matrix = matrix if matrix is not None else {}
    attempted = attempted if attempted is not None else set()
    attempts = successes = 0
    # Finite bound is determined by the number of directional pairs, not a
    # hardcoded arbitrary quota. Usually converges in 1-3 iterations.
    count = len(set(map(str, selected)))
    max_rounds = max(1, count * (count - 1) + 1)
    for _ in range(max_rounds):
        rows, missing = optimizer(profile, selected, catalog, day, park,
            travel_minutes=matrix, buffer_min=buffer_min,
            ride_duration_min=ride_duration_min, include_ids=True)
        pairs = []
        for prev, current in zip(rows, rows[1:]):
            pair = (str(prev['_id']), str(current['_id']))
            if pair not in attempted and pair not in matrix and all(x in coords for x in pair):
                pairs.append(pair)
        pairs = list(dict.fromkeys(pairs))
        if not pairs:
            break
        attempted.update(pairs)
        attempts += len(pairs)
        def resolve(pair):
            try:
                result = fetch(pair)
                distance = float(result['distance_m']) if result else math.nan
                if math.isfinite(distance) and distance > 0:
                    return pair, result
            except Exception:
                pass
            return pair, None
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            for pair, result in pool.map(resolve, pairs):
                if result:
                    matrix[pair] = float(result['duration_min'])
                    successes += 1
    # One final calculation ensures returned times reflect newly loaded legs.
    rows, missing = optimizer(profile, selected, catalog, day, park,
        travel_minutes=matrix, buffer_min=buffer_min,
        ride_duration_min=ride_duration_min, include_ids=True)
    for row in rows:
        row.pop('_id', None)
    unknown = sum(row.get('Rota verificada') == 'Não' for row in rows)
    return rows, missing, {'consultadas': attempts, 'confirmadas': successes,
                           'nao_verificadas': unknown}
