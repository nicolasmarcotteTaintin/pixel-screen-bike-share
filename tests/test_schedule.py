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


def test_off_enabled_gate():
    window = {"off_start": "21:00", "off_end": "08:00"}
    assert is_off_now({**window, "off_enabled": True}, _at(22)) is True
    assert is_off_now({**window, "off_enabled": False}, _at(22)) is False


def test_sunset_window(monkeypatch):
    import pixel_transit.schedule as sched

    monkeypatch.setattr(sched, "montreal_sunset_minutes", lambda now: 20 * 60 + 30)  # 20:30
    config = {"off_start": "sunset", "off_end": "08:00"}
    assert is_off_now(config, _at(21)) is True       # after sunset
    assert is_off_now(config, _at(20, 15)) is False  # before sunset
    assert is_off_now(config, _at(3)) is True        # overnight until 08:00
    assert is_off_now(config, _at(9)) is False


def test_sunset_to_sunrise_window(monkeypatch):
    import pixel_transit.schedule as sched

    monkeypatch.setattr(sched, "montreal_sunset_minutes", lambda now: 20 * 60)  # 20:00
    monkeypatch.setattr(sched, "montreal_sunrise_minutes", lambda now: 5 * 60)  # 05:00
    config = {"off_start": "sunset", "off_end": "sunrise"}
    assert is_off_now(config, _at(22)) is True    # night
    assert is_off_now(config, _at(4)) is True     # before sunrise
    assert is_off_now(config, _at(6)) is False    # after sunrise
    assert is_off_now(config, _at(12)) is False   # midday


def test_sunset_module_plausible():
    import time

    from pixel_transit.sun import montreal_sunset_minutes

    minute = montreal_sunset_minutes(time.struct_time((2026, 6, 20, 12, 0, 0, 5, 171, -1)))
    assert minute is None or 0 <= minute < 24 * 60
