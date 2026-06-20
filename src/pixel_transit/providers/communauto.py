"""Communauto car-sharing — Reservauto front-office REST API.

Communauto has two systems:

* **FLEX** — free-floating cars you pick up and drop anywhere in the zone
  (``Vehicle/FreeFloatingAvailability``). These have coordinates but no address,
  so their "location" on the display is a compass direction from home.
* **Station** — round-trip cars attached to named stations
  (``StationAvailability``). Their location is the station name.

For both systems the display shows the **distance** from a configured home point
and a **location** label, sorted nearest-first.
"""

from __future__ import annotations

import logging
import math
import time
from typing import Any

import requests

from ..geo import bearing, haversine_m
from .base import CarRow, CarShareView

API_BASE = "https://restapifrontoffice.reservauto.net/api/v2"
REQUEST_TIMEOUT_SECONDS = 6
REQUEST_RETRIES = 3
HEADERS = {"User-Agent": "pixel-transit/1.0", "Accept": "application/json"}


class CommunautoProvider:
    kind = "carshare"
    name = "communauto"
    display_name = "Communauto"
    logo_filename = "communauto_logo_27.png"
    fallback_text = "CA"

    def fetch(self, config: dict[str, Any]) -> CarShareView:
        settings = config.get("communauto", {})
        home = settings.get("home", {})
        home_lat = float(home.get("lat", 45.5019))
        home_lon = float(home.get("lon", -73.5674))
        city_id = int(settings.get("city_id", 59))
        radius_km = float(settings.get("radius_km", 2.0))
        services = [s.lower() for s in settings.get("services", ["flex", "station"])]
        max_rows = int(settings.get("max_rows", 3))

        box = _bounding_box(home_lat, home_lon, radius_km)

        flex_rows: list[CarRow] = []
        flex_count = 0
        if "flex" in services:
            flex_rows, flex_count = self._fetch_flex(city_id, box, home_lat, home_lon)

        station_rows: list[CarRow] = []
        station_count = 0
        if "station" in services:
            station_rows, station_count = self._fetch_stations(city_id, box, home_lat, home_lon)

        rows = _select_rows(flex_rows, station_rows, max_rows)
        return CarShareView(
            rows=rows,
            flex_count=flex_count,
            station_count=station_count,
        )

    def _fetch_flex(
        self, city_id: int, box: dict[str, float], home_lat: float, home_lon: float
    ) -> tuple[list[CarRow], int]:
        params = {"CityId": city_id, **box}
        data = _get(f"{API_BASE}/Vehicle/FreeFloatingAvailability", params)
        vehicles = data.get("vehicles", []) or []
        rows: list[CarRow] = []
        for vehicle in vehicles:
            if not vehicle.get("satisfiesFilters", True):
                continue
            location = vehicle.get("vehicleLocation", {}) or {}
            lat, lon = location.get("latitude"), location.get("longitude")
            if lat is None or lon is None:
                continue
            distance = haversine_m(home_lat, home_lon, float(lat), float(lon))
            rows.append(
                CarRow(
                    label="FLEX",
                    distance_m=distance,
                    kind="flex",
                    direction=bearing(home_lat, home_lon, float(lat), float(lon)),
                )
            )
        rows.sort(key=lambda row: row.distance_m)
        total = int(data.get("totalNbVehicles", len(rows)) or len(rows))
        return rows, total

    def _fetch_stations(
        self, city_id: int, box: dict[str, float], home_lat: float, home_lon: float
    ) -> tuple[list[CarRow], int]:
        now = time.localtime()
        start = time.strftime("%Y-%m-%dT%H:%M:%S", now)
        end = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(time.time() + 3600))
        params = {"CityId": city_id, **box, "StartDate": start, "EndDate": end}
        data = _get(f"{API_BASE}/StationAvailability", params)
        stations = data.get("stations", []) or []
        rows: list[CarRow] = []
        for station in stations:
            if not station.get("satisfiesFilters") or station.get("recommendedVehicleId") is None:
                continue
            location = station.get("stationLocation", {}) or {}
            lat, lon = location.get("latitude"), location.get("longitude")
            if lat is None or lon is None:
                continue
            distance = haversine_m(home_lat, home_lon, float(lat), float(lon))
            rows.append(
                CarRow(
                    label=str(station.get("stationName", "STATION")),
                    distance_m=distance,
                    kind="station",
                    direction=bearing(home_lat, home_lon, float(lat), float(lon)),
                )
            )
        rows.sort(key=lambda row: row.distance_m)
        return rows, len(rows)


def _bounding_box(lat: float, lon: float, radius_km: float) -> dict[str, float]:
    d_lat = radius_km / 111.32
    d_lon = radius_km / (111.32 * max(0.01, math.cos(math.radians(lat))))
    return {
        "MaxLatitude": lat + d_lat,
        "MinLatitude": lat - d_lat,
        "MaxLongitude": lon + d_lon,
        "MinLongitude": lon - d_lon,
    }


def _select_rows(flex: list[CarRow], station: list[CarRow], max_rows: int) -> list[CarRow]:
    """Nearest-first overall, but guarantee at least one row of each available kind."""
    combined = sorted(flex + station, key=lambda row: row.distance_m)
    chosen = combined[:max_rows]
    if flex and station:
        kinds = {row.kind for row in chosen}
        for missing, source in (("flex", flex), ("station", station)):
            if missing not in kinds and chosen:
                chosen[-1] = source[0]
                chosen.sort(key=lambda row: row.distance_m)
                kinds = {row.kind for row in chosen}
    return chosen


def _get(url: str, params: dict[str, Any]) -> dict[str, Any]:
    last_error: Exception | None = None
    for attempt in range(1, REQUEST_RETRIES + 1):
        try:
            response = requests.get(url, params=params, headers=HEADERS, timeout=REQUEST_TIMEOUT_SECONDS)
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, ValueError) as exc:
            last_error = exc
            logging.warning("Communauto fetch failed on attempt %s/%s: %s", attempt, REQUEST_RETRIES, exc)
            if attempt < REQUEST_RETRIES:
                time.sleep(0.5 * attempt)
    raise RuntimeError(f"Communauto fetch failed after {REQUEST_RETRIES} attempts: {last_error}")


def provider() -> CommunautoProvider:
    return CommunautoProvider()
