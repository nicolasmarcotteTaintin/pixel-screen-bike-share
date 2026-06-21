from pixel_transit.providers.registry import active_networks


def test_velo_only():
    assert active_networks("velo", "avelo") == ["avelo"]
    assert active_networks("velo", "bixi") == ["bixi"]


def test_communauto_only():
    assert active_networks("communauto", "avelo") == ["communauto"]


def test_alternation_order():
    assert active_networks("velo_communauto", "avelo") == ["avelo", "communauto"]
    assert active_networks("velo_communauto", "bixi") == ["bixi", "communauto"]


def test_non_bike_network_falls_back_to_avelo():
    # If "network" isn't a bike system, the vélo side defaults to àVélo.
    assert active_networks("velo_communauto", "communauto") == ["avelo", "communauto"]
