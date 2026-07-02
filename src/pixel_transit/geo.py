"""Geographic helpers: great-circle distance, bearing and human formatting."""

from __future__ import annotations

import math

_DIRECTIONS = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in metres between two WGS84 points."""
    radius = 6_371_000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * radius * math.asin(min(1.0, math.sqrt(a)))


def bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> str:
    """8-point compass direction from point 1 to point 2 (e.g. ``"NE"``)."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_lambda = math.radians(lon2 - lon1)
    x = math.sin(d_lambda) * math.cos(phi2)
    y = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(d_lambda)
    angle = (math.degrees(math.atan2(x, y)) + 360) % 360
    return _DIRECTIONS[round(angle / 45) % 8]


def format_distance(metres: float) -> str:
    """Compact distance label that fits the narrow display: ``"350M"`` or ``"1.2KM"``."""
    if metres < 1000:
        return f"{int(round(metres))}M"
    km = metres / 1000.0
    if km < 10:
        return f"{km:.1f}KM"
    return f"{int(round(km))}KM"
