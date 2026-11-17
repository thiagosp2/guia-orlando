"""Conservative queue forecasts using only observed local wait samples.

No historical evidence => no numerical forecast. All times use Orlando timezone.
"""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import math
import statistics

TZ = ZoneInfo('America/New_York')


def forecast_wait(observations, ride_id, now=None, horizons=(30, 60, 120), min_days=3):
    """Forecast using day-of-week/time-of-day historical analogs.

    observations: iterable of (ride_id, ISO UTC timestamp, wait_min).
    Excludes current calendar day to avoid future leakage and correlated snapshots.
    Returns a mapping horizon -> {estimate, low, high, days} or None.
    """
    now = now or datetime.now(TZ)
    if now.tzinfo is None:
        raise ValueError('now must have a timezone')
    now = now.astimezone(TZ)
    parsed = []
    for rid, timestamp, wait in observations:
        if str(rid) != str(ride_id):
            continue
        try:
            when = datetime.fromisoformat(str(timestamp).replace('Z', '+00:00')).astimezone(TZ)
            value = float(wait)
        except (TypeError, ValueError, OverflowError):
            continue
        if not math.isfinite(value) or not 0 <= value <= 600 or when >= now or when.date() == now.date():
            continue
        parsed.append((when, value))
    result = {}
    for minutes in horizons:
        target = now + timedelta(minutes=minutes)
        if target.date() != now.date():
            result[minutes] = None
            continue
        per_day = {}
        for when, value in parsed:
            if abs((when.hour * 60 + when.minute) - (target.hour * 60 + target.minute)) > 45:
                continue
            # Same weekday preferred, but allow other days to avoid empty samples.
            weight = 2 if when.weekday() == target.weekday() else 1
            per_day.setdefault(when.date(), []).append((value, weight))
        if len(per_day) < min_days:
            result[minutes] = None
            continue
        daily = [(statistics.median(v for v, _ in samples), max(w for _, w in samples)) for samples in per_day.values()]
        weighted = sorted((v, w) for v, w in daily)
        total = sum(w for _, w in weighted)
        def quantile(p):
            count = 0
            for v, w in weighted:
                count += w
                if count >= p * total:
                    return v
            return weighted[-1][0]
        result[minutes] = {'estimate': round(quantile(.5)), 'low': round(quantile(.2)),
                           'high': round(quantile(.8)), 'days': len(per_day)}
    return result


def queue_alerts(previous, current, threshold=20):
    """Detect material changes in queue length and operating status."""
    alerts = []
    for rid, item in current.items():
        old = previous.get(rid)
        if not old:
            continue
        old_status, old_wait = old
        status, wait = item
        if old_status == 'OPERATING' and status != 'OPERATING':
            alerts.append((rid, 'Fechou ou deixou de operar'))
        elif old_status != 'OPERATING' and status == 'OPERATING':
            alerts.append((rid, 'Voltou a operar'))
        elif old_wait is not None and wait is not None and abs(wait - old_wait) >= threshold:
            alerts.append((rid, f'Fila mudou {wait-old_wait:+.0f} min'))
    return alerts
