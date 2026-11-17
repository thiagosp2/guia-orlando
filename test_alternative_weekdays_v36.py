import unittest
from datetime import date
import pandas as pd
from day_optimizer import recommend_date_options

class AlternativeWeekdays(unittest.TestCase):
    def test_second_option_changes_weekday_for_each_park(self):
        records=[]
        for park in ['A','B','C']:
            for day,wait in [(0,10),(1,20),(2,30),(3,40),(4,50)]:
                records.append(dict(parque=park,dia_semana=day,fila_media=wait,dias_amostrados=4,prioridade_media=wait))
        plans=recommend_date_options(pd.DataFrame(records),date(2026,11,30),date(2026,12,11),['A','B','C'])
        self.assertEqual(len(plans),2)
        a={p:d.weekday() for p,d,_,_ in plans[0]}
        b={p:d.weekday() for p,d,_,_ in plans[1]}
        self.assertTrue(all(a[p]!=b[p] for p in a))
        self.assertEqual(len({d for _,d,_,_ in plans[1]}),3)
    def test_no_false_alternative_same_weekday(self):
        records=pd.DataFrame([dict(parque='A',dia_semana=0,fila_media=20,dias_amostrados=4,prioridade_media=20)])
        plans=recommend_date_options(records,date(2026,11,30),date(2026,12,14),['A'])
        self.assertEqual(len(plans),1)
if __name__=='__main__':unittest.main()
