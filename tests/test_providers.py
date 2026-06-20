import pytest

from pixel_transit.providers.base import CarRow
from pixel_transit.providers.communauto import _bounding_box, _select_rows
from pixel_transit.providers.registry import NETWORK_NAMES, get_provider


def test_registry_known_and_unknown():
    for name in NETWORK_NAMES:
        provider = get_provider(name)
        assert provider.name == name
        assert provider.kind in ("bikeshare", "carshare")
    with pytest.raises(ValueError):
        get_provider("nope")


def test_bounding_box_brackets_home():
    box = _bounding_box(45.5, -73.5, 2.0)
    assert box["MinLatitude"] < 45.5 < box["MaxLatitude"]
    assert box["MinLongitude"] < -73.5 < box["MaxLongitude"]


def test_select_rows_guarantees_both_kinds():
    flex = [CarRow("FLEX", 100, "flex"), CarRow("FLEX", 150, "flex")]
    station = [CarRow("A", 800, "station")]
    rows = _select_rows(flex, station, max_rows=3)
    kinds = {r.kind for r in rows}
    assert kinds == {"flex", "station"}


def test_select_rows_respects_max():
    flex = [CarRow("FLEX", d, "flex") for d in (100, 200, 300, 400)]
    rows = _select_rows(flex, [], max_rows=2)
    assert len(rows) == 2
