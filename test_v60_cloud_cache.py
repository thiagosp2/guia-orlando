from datetime import date
from unittest.mock import patch
from tempfile import TemporaryDirectory
from pathlib import Path
from planner_cache import collect_history


def test_cloud_hit_prevents_api():
    day=date(2026,11,10)
    with TemporaryDirectory() as tmp:
        with patch('cloud_history.enabled',return_value=True), patch('cloud_history.read',return_value={day:{'events':[1]}}), patch('cloud_history.write'):
            result,errors,stats=collect_history(['park'],[day],lambda *args: (_ for _ in ()).throw(AssertionError('API chamada')),db=Path(tmp)/'test.sqlite3')
        assert result['park'][day]=={'events':[1]}
        assert stats['cloud_hits']==1 and stats['api_requests']==0


def test_api_miss_written_to_cloud():
    day=date(2026,11,10)
    with TemporaryDirectory() as tmp:
        with patch('cloud_history.enabled',return_value=True), patch('cloud_history.read',return_value={}), patch('cloud_history.write',return_value=True) as write:
            result,errors,stats=collect_history(['park'],[day],lambda *args: {'events':[2]},db=Path(tmp)/'test.sqlite3')
        assert stats['api_requests']==1 and stats['successful_requests']==1
        write.assert_called_once()


def test_cloud_failure_falls_back_to_api():
    import requests
    day=date(2026,11,10)
    with TemporaryDirectory() as tmp:
        with patch('cloud_history.enabled',return_value=True), patch('cloud_history.read',side_effect=requests.ConnectionError('offline')), patch('cloud_history.write',return_value=True):
            result,errors,stats=collect_history(['park'],[day],lambda *args: {'events':[3]},db=Path(tmp)/'test.sqlite3')
        assert result['park'][day]=={'events':[3]}
        assert stats['cloud_errors']
