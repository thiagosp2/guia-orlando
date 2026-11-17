from park_map import make_park_map, valid_point


def test_invalid_coords_do_not_enter_map():
    assert not valid_point(float('nan'), -81.5)
    assert not valid_point(0, 0)
    assert valid_point(28.42, -81.58)


def test_map_loads_attractions_areas_before_route():
    m = make_park_map([
        {'id':'a','name':'Space Mountain','lat':28.419,'lon':-81.578,'area':'Tomorrowland'},
        {'id':'b','name':'TRON','lat':28.420,'lon':-81.579,'area':'Tomorrowland'}], 'a','b')
    html=m
    assert '<svg' in html
    assert 'Tomorrowland' in html
    assert 'Space Mountain' in html
    assert 'Rota de caminhada verificada' not in html


def test_map_only_draws_verified_route_when_provided():
    locations=[{'id':'a','name':'A','lat':28.419,'lon':-81.578,'area':'Fantasyland'},
               {'id':'b','name':'B','lat':28.420,'lon':-81.579,'area':'Fantasyland'}]
    html=make_park_map(locations,'a','b',[(28.419,-81.578),(28.4195,-81.5785),(28.420,-81.579)])
    assert 'Rota de caminhada verificada' in html
