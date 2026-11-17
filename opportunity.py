"""Relative queue opportunities based on observed, per-ride historical waits."""
import pandas as pd


def build_baselines(observations, now=None, min_samples=6, min_days=2):
    """Observations: ride_id, observed_at (ISO UTC), wait_min. Prefer ±90m local time.

    Require distinct calendar dates to avoid presenting repeated polling as independent history.
    """
    if not observations:
        return {}
    now = pd.Timestamp.now(tz='UTC') if now is None else pd.Timestamp(now)
    if now.tzinfo is None:
        now = now.tz_localize('UTC')
    rows = pd.DataFrame(observations, columns=['ride_id','observed_at','wait_min'])
    rows['observed_at'] = pd.to_datetime(rows.observed_at, utc=True, errors='coerce')
    rows['wait_min'] = pd.to_numeric(rows.wait_min, errors='coerce')
    rows = rows.dropna(subset=['observed_at','wait_min'])
    rows = rows[(rows.wait_min >= 0) & (rows.wait_min <= 300) & (rows.observed_at < now)]
    if rows.empty:
        return {}
    local = rows.observed_at.dt.tz_convert('America/New_York')
    rows['local_date'] = local.dt.date
    rows['minute'] = local.dt.hour * 60 + local.dt.minute
    now_local = now.tz_convert('America/New_York')
    target = now_local.hour * 60 + now_local.minute
    distance = (rows.minute - target).abs()
    rows['near_time'] = distance <= 90
    results = {}
    for rid, group in rows.groupby('ride_id'):
        # Same-hour comparisons are preferable; fallback to all-hours only if adequate.
        close = group[group.near_time]
        candidate = close if len(close) >= min_samples and close.local_date.nunique() >= min_days else group
        if len(candidate) < min_samples or candidate.local_date.nunique() < min_days:
            continue
        # First aggregate by date, to prevent over-weighting frequently polled days.
        per_day = candidate.groupby('local_date').wait_min.mean()
        mean = float(per_day.mean())
        if mean <= 0:
            continue
        results[str(rid)] = {
            'mean': round(mean,1), 'peak': round(float(candidate.wait_min.quantile(.90)),1),
            'samples': len(candidate), 'days': len(per_day),
            'same_hour': candidate is close,
        }
    return results


def rank_opportunities(ranked, baselines, bonus_weight=22.0):
    """Lower adjusted index is better. No baseline -> original ranking unchanged."""
    if ranked.empty:
        return ranked.copy()
    result = ranked.copy()
    def calc(row):
        b = baselines.get(str(row['id']))
        wait = row['Fila (min)']
        if b is None or pd.isna(wait) or b['mean'] <= 0:
            return pd.Series({'Média histórica (min)':float('nan'), 'Pico histórico P90 (min)':float('nan'),
                              'Economia (min)':float('nan'), 'Base histórica':'Indisponível', 'Oportunidade': 'Sem histórico suficiente',
                              'Índice ajustado':float(row['Índice'])})
        saving = b['mean'] - float(wait)
        relative = max(0., min(saving / b['mean'], 1.))
        # Avoid treating small differences as reliable signals.
        label = ('🟢 Boa oportunidade' if saving >= 10 and relative >= .25
                 else '🟡 Abaixo da média' if saving >= 5 and relative >= .10
                 else 'Sem vantagem relevante')
        return pd.Series({'Média histórica (min)':b['mean'],'Pico histórico P90 (min)':b['peak'],
                          'Economia (min)':round(saving,1),'Base histórica': ('Mesmo horário' if b['same_hour'] else 'Dia inteiro'), 'Oportunidade':label,
                          'Índice ajustado':round(float(row['Índice']) - bonus_weight * relative,2)})
    result = pd.concat([result, result.apply(calc,axis=1)],axis=1)
    return result.sort_values(['Imperdível','Índice ajustado','Fila (min)'],ascending=[False,True,True])
