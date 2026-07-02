from pixel_transit.geo import bearing, format_distance, haversine_m


def test_haversine_known_distance():
    # Montréal downtown to ~1 km north; allow a small tolerance.
    d = haversine_m(45.5019, -73.5674, 45.5109, -73.5674)
    assert 950 < d < 1050


def test_haversine_zero():
    assert haversine_m(45.5, -73.5, 45.5, -73.5) == 0


def test_bearing_cardinals():
    assert bearing(45.5, -73.5, 45.6, -73.5) == "N"
    assert bearing(45.5, -73.5, 45.4, -73.5) == "S"
    assert bearing(45.5, -73.5, 45.5, -73.4) == "E"
    assert bearing(45.5, -73.5, 45.5, -73.6) == "W"


def test_format_distance():
    assert format_distance(350) == "350M"
    assert format_distance(1200) == "1.2KM"
    assert format_distance(15000) == "15KM"
