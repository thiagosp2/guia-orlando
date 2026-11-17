"""Shared decision metrics across planning, integrated analysis, and weekday ranking.

Historical hourly waits are averaged within each date; dates receive equal weight.
This is an observational weekday indicator, not a forecast of a particular future date.
"""
from day_optimizer import day_metric, weekday_baselines
import pandas as pd


def collect_day_metrics(histories, parks, dates, park_ids, selected_by_park=None, hours=range(10, 19)):
    selected_by_park = selected_by_park or {}
    rows = []
    errors = []
    for park in parks:
        for day in dates:
            payload = histories.get(park_ids[park], {}).get(day)
            if payload is None:
                continue
            try:
                metric = day_metric(payload, day, hours=hours,
                                    selected_ids=selected_by_park.get(park) or ())
                if metric is not None:
                    rows.append({'parque': park, 'data': day, **metric})
            except (ValueError, TypeError, KeyError) as exc:
                errors.append(f'{park} {day:%d/%m}: {exc}')
    return rows, errors


def weekday_summary(rows, minimum_days=3):
    baselines = weekday_baselines(rows)
    if baselines.empty:
        return baselines
    return baselines[baselines['dias_amostrados'] >= minimum_days].copy()


def ordered_weekdays(rows, park, minimum_days=3):
    baseline = weekday_summary(rows, minimum_days)
    if baseline.empty:
        return []
    group = baseline[baseline['parque'] == park]
    return sorted(group.to_dict('records'), key=lambda r:(r['fila_media'],r['dia_semana']))
