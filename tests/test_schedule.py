import time

from pixel_transit.schedule import is_off_now


def _at(hour, minute=0):
    return time.struct_time((2026, 6, 20, hour, minute, 0, 5, 171, -1))


def test_overnight_window():
    config = {"off_start": "21:00", "off_end": "08:00"}
    assert is_off_now(config, _at(22)) is True
    assert is_off_now(config, _at(3)) is True
    assert is_off_now(config, _at(7, 59)) is True
    assert is_off_now(config, _at(8)) is False
    assert is_off_now(config, _at(12)) is False
    assert is_off_now(config, _at(20, 59)) is False
    assert is_off_now(config, _at(21)) is True


def test_daytime_window():
    config = {"off_start": "09:00", "off_end": "17:00"}
    assert is_off_now(config, _at(12)) is True
    assert is_off_now(config, _at(8)) is False
    assert is_off_now(config, _at(17)) is False


def test_disabled_when_empty_or_equal():
    assert is_off_now({"off_start": "", "off_end": ""}, _at(3)) is False
    assert is_off_now({"off_start": "08:00", "off_end": "08:00"}, _at(8)) is False
    assert is_off_now({}, _at(3)) is False
