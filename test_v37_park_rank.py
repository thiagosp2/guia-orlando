import unittest
from datetime import date
import pandas as pd
from day_optimizer import recommend_date_options
from planned_itinerary import plan_ride_hours

class RankedParkOptions(unittest.TestCase):
    def test_each_park_uses_its_own_two_best_weekdays(self):
        waits={'Magic Kingdom':{3:20,6:30,0:60},'EPCOT':{1:10,4:20,5:50}}
        data=[{'parque':p,'dia_semana':d,'fila_media':w,'prioridade_media':w,'dias_amostrados':4} for p,days in waits.items() for d,w in days.items()]
        plans=recommend_date_options(pd.DataFrame(data),date(2026,11,29),date(2026,12,9),list(waits))
        self.assertEqual(len(plans),2)
        for i,expected in enumerate(({'Magic Kingdom':3,'EPCOT':1},{'Magic Kingdom':6,'EPCOT':4})):
            self.assertEqual({p:d.weekday() for p,d,_,_ in plans[i]},expected)
    def test_different_day_hourly_profiles(self):
        # The planning stage must use the weekday-specific profile returned by best_hours.
        for day,hour in [(date(2026,12,3),'10:00'),(date(2026,12,6),'14:00')]:
            profile=pd.DataFrame([{'id':'ride','Horário':hour,'Fila típica (min)':20,'Dias observados':3}])
            rows,missing=plan_ride_hours(profile,['ride'],{'ride':'Ride'},day,'Magic Kingdom')
            self.assertEqual(rows[0]['Horário'],hour)
            self.assertEqual(rows[0]['Dia'],('Quinta' if day.weekday()==3 else 'Domingo'))
            self.assertFalse(missing)
if __name__=='__main__':unittest.main()
