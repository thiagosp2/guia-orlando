from datetime import date
import pandas as pd
from on_demand_routes import optimize_on_demand
from planned_itinerary import optimize_ride_route


def profile():
    return pd.DataFrame([{'id':rid,'Horário':f'{hour:02d}:00','Fila típica (min)':10,'Dias observados':4}
        for rid in ('A','B','C') for hour in range(9,16)])


def test_fetch_only_used_directional_legs_and_reuse():
    calls=[]
    def fetch(pair):
        calls.append(pair)
        return {'distance_m':400, 'duration_min':6}
    matrix={}; attempted=set()
    args=(profile(),['A','B','C'],{'A':'A','B':'B','C':'C'},date(2026,11,19),'Park',
          {'A':(1,1),'B':(2,2),'C':(3,3)},fetch,optimize_ride_route)
    rows, missing, stats=optimize_on_demand(*args,matrix=matrix,attempted=attempted)
    assert len(rows)==3 and not missing
    assert 2 <= stats['consultadas'] <= 6
    assert len(matrix)==stats['consultadas']
    assert all(r['Rota verificada']=='Sim' for r in rows)
    rows2, missing2, stats2=optimize_on_demand(*args,matrix=matrix,attempted=attempted)
    assert stats2['consultadas']==0
    assert len(calls)==stats['consultadas']


def test_failed_route_not_fabricated_or_retried():
    calls=[]
    def fetch(pair):
        calls.append(pair)
        raise ConnectionError('offline')
    rows, missing, stats=optimize_on_demand(profile(),['A','B','C'],{},date(2026,11,19),
        'Park',{'A':(1,1),'B':(2,2),'C':(3,3)},fetch,optimize_ride_route)
    assert len(rows)==3
    assert stats['nao_verificadas']==2
    assert all(r['Caminhada (min)'] is None for r in rows[1:])
    assert len(calls)==2
