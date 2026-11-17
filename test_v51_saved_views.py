import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch
import saved_views

class TestSavedViews(unittest.TestCase):
    def test_only_parameters(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(saved_views,'DB',Path(tmp)/'saved.sqlite3'):
            state={'planned_start':date(2026,11,26),'planned_parks':['Magic Kingdom'], 'v47_ranking_parks':['EPCOT'], 'api_key_input':'SECRET','last_metadata_foo':{'a':1}}
            saved_views.save(state)
            restored={}
            saved_views.restore(restored)
            self.assertEqual(restored['planned_start'],date(2026,11,26))
            self.assertEqual(restored['planned_parks'],['Magic Kingdom'])
            self.assertNotIn('api_key_input',restored)
            self.assertNotIn('last_metadata_foo',restored)
            saved_views.clear(restored)
            again={}; saved_views.restore(again)
            self.assertFalse(again)
if __name__=='__main__': unittest.main()
