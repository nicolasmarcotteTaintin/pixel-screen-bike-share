"""Shared GBFS plumbing and the generic bike-share provider.

BIXI (GBFS v2) and àVélo (GBFS v3) both expose ``station_information`` and
``station_status`` feeds. This module fetches and merges them, then builds a
:class:`BikeShareView` from a network's column layout.
"""

from __future__ import annotations

import logging
import time
import unicodedata
from typing import Any

import requests

from .base import BikeShareView, Column, StationRow

REQUEST_TIMEOUT_SECONDS = 5
REQUEST_RETRIES = 3

STREET_ABBREVIATIONS = {
    "AVENUE": "AVE",
    "AV": "AVE",
    "BOULEVARD": "BOUL",
    "RUE": "",
    "CHEMIN": "CH",
    "SAINT": "ST",
    "SAINTE": "STE",
    "STREET": "ST",
    "PLACE": "PL",
    "MONT-ROYAL": "MONT-R",
    "DU": "",
    "DE": "",
    "DES": "",
}


def fetch_gbfs(url: str) -> dict[str, Any]:
    last_error: Exception | None = None
    for attempt in range(1, REQUEST_RETRIES + 1):
        try:
            response = requests.get(url, timeout=REQUEST_TIMEOUT_SECONDS)
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, ValueError) as exc:
            last_error = exc
            logging.warning("GBFS fetch failed on attempt %s/%s: %s", attempt, REQUEST_RETRIES, exc)
            if attempt < REQUEST_RETRIES:
                time.sleep(0.5 * attempt)
    raise RuntimeError(f"GBFS fetch failed after {REQUEST_RETRIES} attempts: {last_error}")


def _merge_stations(information: list[dict], statuses: list[dict]) -> dict[str, dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}
    for station in information:
        station_id = str(station.get("station_id", ""))
        if station_id:
            by_id[station_id] = station.copy()
    for status in statuses:
        station_id = str(status.get("station_id", ""))
        if not station_id:
            continue
        by_id.setdefault(station_id, {})["station_id"] = station_id
        by_id[station_id].update(status)
    return by_id


def _lookup(by_id: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Index stations by both ``station_id`` and public ``short_name``."""
    lookup: dict[str, dict[str, Any]] = {}
    for station in by_id.values():
        station_id = str(station.get("station_id", ""))
        short_name = str(station.get("short_name", ""))
        if station_id:
            lookup[station_id] = station
        if short_name:
            lookup[short_name] = station
    return lookup


def station_raw_name(station: dict[str, Any]) -> str:
    """Station name, handling GBFS v3 where ``name`` is a list of {text, language}."""
    name = station.get("name", station.get("station_id", ""))
    if isinstance(name, list):
        for entry in name:
            if isinstance(entry, dict) and entry.get("text"):
                return str(entry["text"])
        return ""
    return str(name)


def _abbreviate_part(part: str) -> str:
    words = [STREET_ABBREVIATIONS.get(word, word) for word in part.upper().split()]
    return " ".join(word for word in words if word)


def station_name_label(name: str, fallback: str) -> str:
    """Abbreviated ASCII uppercase label from the first part of the name (before '/')."""
    normalized = unicodedata.normalize("NFKD", name)
    ascii_name = normalized.encode("ascii", "ignore").decode("ascii")
    return _abbreviate_part(ascii_name.split("/")[0]) or fallback


def count_total_bikes(station: dict[str, Any]) -> int:
    """Total bikes available, summing vehicle types when no direct count is given."""
    direct = station.get("num_bikes_available")
    if direct is not None:
        return int(direct or 0)
    total = 0
    for item in station.get("vehicle_types_available") or []:
        if isinstance(item, dict):
            total += int(item.get("count", 0) or 0)
    return total


def count_ebikes(station: dict[str, Any]) -> int:
    direct = station.get("num_ebikes_available")
    if direct is not None:
        return int(direct or 0)
    total = 0
    bike_types = station.get("num_bikes_available_types") or station.get("vehicle_types_available") or []
    if isinstance(bike_types, dict):
        bike_types = [bike_types]
    for item in bike_types:
        if not isinstance(item, dict):
            continue
        for key in ("ebike", "electric", "electric_bike"):
            if key in item:
                total += int(item[key] or 0)
        if str(item.get("vehicle_type_id", "")).lower() in {"ebike", "electric", "electric_bike"}:
            total += int(item.get("count", 0) or 0)
    return total


def count_docks(station: dict[str, Any]) -> int:
    return int(station.get("num_docks_available", 0) or 0)


# Maps a column key to the function that reads its value from a merged station.
VALUE_READERS = {
    "bike": count_total_bikes,
    "bolt": count_ebikes,
    "park": count_docks,
}


class BikeShareProvider:
    """Generic GBFS bike-share provider parameterised by feed URLs and columns."""

    kind = "bikeshare"

    def __init__(
        self,
        *,
        name: str,
        display_name: str,
        information_url: str,
        status_url: str,
        columns: list[Column],
        name_max_width: int,
        logo_filename: str,
        fallback_text: str,
    ) -> None:
        self.name = name
        self.display_name = display_name
        self.information_url = information_url
        self.status_url = status_url
        self.columns = columns
        self.name_max_width = name_max_width
        self.logo_filename = logo_filename
        self.fallback_text = fallback_text

    def fetch(self, config: dict[str, Any]) -> BikeShareView:
        favorites = [str(s) for s in config.get("favorite_stations", [])]
        information = fetch_gbfs(self.information_url).get("data", {}).get("stations", [])
        statuses = fetch_gbfs(self.status_url).get("data", {}).get("stations", [])
        lookup = _lookup(_merge_stations(information, statuses))

        rows: list[StationRow] = []
        for favorite_id in favorites:
            station = lookup.get(str(favorite_id))
            if not station:
                logging.warning("Favorite station %s was not found in GBFS data", favorite_id)
                continue
            name = station_name_label(station_raw_name(station), self.fallback_text)
            values = [VALUE_READERS[column.key](station) for column in self.columns]
            rows.append(StationRow(name=name, values=values))

        return BikeShareView(columns=self.columns, rows=rows, name_max_width=self.name_max_width)
