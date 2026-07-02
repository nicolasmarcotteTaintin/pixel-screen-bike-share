"""Sunrise/sunset times for a location, with no external dependencies.

Uses the standard "sunrise equation" (NOAA low-precision approximation),
accurate to about a minute — enough to switch a display off around dusk and
back on at dawn. Times are converted to local time via the system timezone, so
on the Pi (configured for America/Toronto) they yield Montréal local time.
"""

from __future__ import annotations

import math
import time

# Downtown Montréal (used for the "follow the sun" quiet-hours option).
MONTREAL_LAT = 45.5019
MONTREAL_LON = -73.5674

_UNIX_EPOCH_JD = 2440587.5


def _sun_epochs(lat: float, lon: float, year: int, month: int, day: int) -> tuple[float | None, float | None]:
    """(sunrise, sunset) as UTC epoch seconds for the date, or (None, None) in polar day/night."""
    a = (14 - month) // 12
    yy = year + 4800 - a
    mm = month + 12 * a - 3
    jdn = day + (153 * mm + 2) // 5 + 365 * yy + yy // 4 - yy // 100 + yy // 400 - 32045
    n = jdn - 2451545 + 0.0008
    # Signed longitude (east positive); west of Greenwich shifts solar noon later.
    j_star = n - lon / 360.0

    m_anom = math.radians((357.5291 + 0.98560028 * j_star) % 360)
    center = (1.9148 * math.sin(m_anom)
              + 0.0200 * math.sin(2 * m_anom)
              + 0.0003 * math.sin(3 * m_anom))
    ecl_lon = math.radians((math.degrees(m_anom) + center + 282.9372) % 360)
    j_transit = (2451545.0 + j_star
                 + 0.0053 * math.sin(m_anom)
                 - 0.0069 * math.sin(2 * ecl_lon))

    declination = math.asin(math.sin(ecl_lon) * math.sin(math.radians(23.44)))
    lat_r = math.radians(lat)
    cos_omega = ((math.sin(math.radians(-0.833)) - math.sin(lat_r) * math.sin(declination))
                 / (math.cos(lat_r) * math.cos(declination)))
    if not -1.0 <= cos_omega <= 1.0:
        return None, None  # sun never rises / never sets at this date+latitude
    omega = math.degrees(math.acos(cos_omega))
    j_rise = j_transit - omega / 360.0
    j_set = j_transit + omega / 360.0
    return (j_rise - _UNIX_EPOCH_JD) * 86400.0, (j_set - _UNIX_EPOCH_JD) * 86400.0


def _local_minutes(epoch: float | None) -> int | None:
    if epoch is None:
        return None
    local = time.localtime(epoch)
    return local.tm_hour * 60 + local.tm_min


def sunset_local_minutes(lat: float, lon: float, now: time.struct_time | None = None) -> int | None:
    """Minute-of-day (local time) of sunset for ``now``'s date, or None if no sunset."""
    now = now or time.localtime()
    _, sunset = _sun_epochs(lat, lon, now.tm_year, now.tm_mon, now.tm_mday)
    return _local_minutes(sunset)


def sunrise_local_minutes(lat: float, lon: float, now: time.struct_time | None = None) -> int | None:
    """Minute-of-day (local time) of sunrise for ``now``'s date, or None if no sunrise."""
    now = now or time.localtime()
    sunrise, _ = _sun_epochs(lat, lon, now.tm_year, now.tm_mon, now.tm_mday)
    return _local_minutes(sunrise)


def montreal_sunset_minutes(now: time.struct_time | None = None) -> int | None:
    """Minute-of-day (local time) of sunset in Montréal for ``now``'s date."""
    return sunset_local_minutes(MONTREAL_LAT, MONTREAL_LON, now)


def montreal_sunrise_minutes(now: time.struct_time | None = None) -> int | None:
    """Minute-of-day (local time) of sunrise in Montréal for ``now``'s date."""
    return sunrise_local_minutes(MONTREAL_LAT, MONTREAL_LON, now)
