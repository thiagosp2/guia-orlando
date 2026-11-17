from datetime import date, timedelta
from concurrent.futures import ThreadPoolExecutor
from planner_cache import collect_history, read_cached


def test_persistent_cache_skips_network(tmp_path):
    db=tmp_path/'cache.sqlite3'
    days=[date(2026,11,1),date(2026,11,2)]
    calls=[]
    def request(park,day):
        calls.append((park,day))
        return {'history':[],'day':day.isoformat()}
    first,errors,stats=collect_history(['mk'],days,request,db=db,max_workers=2)
    assert not errors and stats['api_requests']==2 and stats['cache_hits']==0
    second,errors,stats=collect_history(['mk'],days,request,db=db,max_workers=2)
    assert not errors and stats['api_requests']==0 and stats['cache_hits']==2
    assert len(calls)==2 and first==second


def test_failed_responses_never_cached(tmp_path):
    db=tmp_path/'cache.sqlite3'; day=date(2026,11,1)
    def fail(park,day): raise RuntimeError('HTTP 403')
    _,errors,stats=collect_history(['mk'],[day],fail,db=db,retry_count=0)
    assert len(errors)==1 and stats['failed_requests']==1
    assert not read_cached('mk',[day],db=db)


def test_new_dates_only_fetch_misses(tmp_path):
    db=tmp_path/'cache.sqlite3'; days=[date(2026,11,1),date(2026,11,2)]
    calls=[]
    def request(park,day):
        calls.append(day)
        return {'valid':True}
    collect_history(['mk'],days[:1],request,db=db)
    _,_,stats=collect_history(['mk'],days,request,db=db)
    assert stats['api_requests']==1 and stats['cache_hits']==1 and len(calls)==2
