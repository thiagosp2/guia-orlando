from park_map import make_park_map

def test_remote_tiles_and_area_without_python_tiles():
    locations=[{'id':'a','name':'Space Mountain','lat':28.419,'lon':-81.578,'area':'Tomorrowland'}, {'id':'b','name':'TRON','lat':28.420,'lon':-81.579,'area':'Tomorrowland'}]
    page=make_park_map(locations,fetch_tiles=False)
    assert 'remote-tile' in page
    assert 'tile.openstreetmap.org' in page
    assert 'Tomorrowland' in page
    assert 'Space Mountain' in page
    assert 'zoom-in' in page and 'zoom-out' in page
    assert 'M 25 420' in page
