"""Loading, validating and persisting the JSON configuration.

A single ``network`` key selects which transit network a device shows. Each
network reads the keys it needs: bike-share networks use ``favorite_stations``;
Communauto uses the ``communauto`` block (home point, city, services).
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .providers.registry import MODES, NETWORK_NAMES, active_networks as _active_networks

BASE_DIR = Path(__file__).resolve().parent

CONFIG_PATH = Path(
    os.getenv("PIXEL_TRANSIT_CONFIG_PATH")
    or os.getenv("BIXI_CONFIG_PATH")
    or (BASE_DIR / "config.json")
)

DEFAULT_CONFIG: dict[str, Any] = {
    "network": "avelo",
    "mode": "velo_communauto",
    "language": "fr",
    "rotate_seconds": 10,
    "favorite_stations": ["81", "85", "141"],
    "communauto": {
        "city_id": 59,
        "home": {"lat": 45.5019, "lon": -73.5674},
        "radius_km": 2.0,
        "services": ["flex", "station"],
        "max_rows": 3,
    },
    "refresh_seconds": 60,
    "brightness": 80,
    "off_start": "",
    "off_end": "",
}


def ensure_config_exists() -> None:
    if not CONFIG_PATH.exists():
        save_config(DEFAULT_CONFIG)


def load_config() -> dict[str, Any]:
    with CONFIG_PATH.open("r", encoding="utf-8") as file:
        config = json.load(file)
    merged = _deep_merge(DEFAULT_CONFIG, config)

    network = str(merged.get("network", "avelo")).lower()
    if network not in NETWORK_NAMES:
        raise ValueError(
            f"Unknown network {network!r} in {CONFIG_PATH}. "
            f"Choose one of: {', '.join(NETWORK_NAMES)}"
        )
    mode = str(merged.get("mode", "velo_communauto")).lower()
    if mode not in MODES:
        raise ValueError(
            f"Unknown mode {mode!r} in {CONFIG_PATH}. Choose one of: {', '.join(MODES)}"
        )
    language = str(merged.get("language", "fr")).lower()
    merged["network"] = network
    merged["mode"] = mode
    merged["language"] = language if language in ("fr", "en") else "fr"
    merged["rotate_seconds"] = max(2, int(merged.get("rotate_seconds", 10)))
    merged["favorite_stations"] = [str(s) for s in merged.get("favorite_stations", [])]
    merged["refresh_seconds"] = max(10, int(merged["refresh_seconds"]))
    merged["brightness"] = max(0, min(100, int(merged["brightness"])))
    return merged


def active_networks(config: dict[str, Any]) -> list[str]:
    """Ordered list of networks the configured mode cycles through."""
    return _active_networks(config["mode"], config["network"])


def save_config(config: dict[str, Any]) -> None:
    CONFIG_PATH.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge ``override`` onto a copy of ``base`` (nested dicts merged)."""
    result = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result
