import unittest
import tempfile
from pathlib import Path
from datetime import date
from live_history import historical_opportunity_samples

class HistoryTests(unittest.TestCase):
    def test_no_data_does_not_fabricate_samples(self):
        with tempfile.TemporaryDirectory() as td:
            def request(pid, day): return {'id':pid,'children':[]}
            samples, errors, stats = historical_opportunity_samples('park',request,today=date(2026,11,17),days=2,db=Path(td)/'cache.sqlite3')
            self.assertEqual(samples,[])
            self.assertEqual(stats['park_days'],2)
            self.assertEqual(stats['valid_samples'],0)

if __name__=='__main__':unittest.main()
