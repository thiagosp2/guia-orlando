from datetime import date
import pandas as pd
from planned_itinerary import optimize_ride_route,itinerary_pdf

def profile(rows):
    return pd.DataFrame([{'id':rid,'Horário':hour,'Fila típica (min)':wait,'Dias observados':4} for rid,hour,wait in rows])

def test_verified_walk_affects_sequence():
    data=profile([('a','10:00',10),('a','11:00',60),('b','10:00',10),('b','11:00',60)])
    # a->b short, b->a long; schedule should favor a->b
    rows,missing=optimize_ride_route(data,['a','b'],{'a':'A','b':'B'},date(2026,12,3),'Magic',
                                     {('a','b'):3,('b','a'):50},buffer_min=5,ride_duration_min=10)
    assert not missing
    assert [r['Atração'] for r in rows]==['A','B']
    assert rows[1]['Caminhada (min)']==3

def test_unknown_walk_not_invented():
    data=profile([('a','10:00',10),('b','11:00',10)])
    rows,missing=optimize_ride_route(data,['a','b'],{'a':'A','b':'B'},date(2026,12,3),'Magic',
                                     {},buffer_min=5,ride_duration_min=10)
    assert not missing
    assert rows[1]['Caminhada (min)'] is None
    assert rows[1]['Rota verificada']=='Não'

def test_duration_and_wait_constrain_slots():
    data=profile([('a','10:00',50),('b','10:00',10),('b','11:00',10)])
    rows,missing=optimize_ride_route(data,['a','b'],{'a':'A','b':'B'},date(2026,12,3),'Magic',
                                     {('a','b'):10,('b','a'):10},buffer_min=5,ride_duration_min=15)
    assert not missing
    assert len(rows)==2

def test_pdf_contains_route_annotation():
    data=profile([('a','10:00',10),('b','11:00',10)])
    day=date(2026,12,3)
    rows,_=optimize_ride_route(data,['a','b'],{'a':'A','b':'B'},day,'Magic',{},5,10)
    pdf=itinerary_pdf([('Magic',day,30.,4)],rows)
    assert pdf.startswith(b'%PDF')
    assert b'caminhada' in pdf.lower()
