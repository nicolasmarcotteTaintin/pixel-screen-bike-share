"""Maps a network name to its provider factory."""

from __future__ import annotations

from .base import Provider
from . import avelo, bixi, communauto

_FACTORIES = {
    "bixi": bixi.provider,
    "avelo": avelo.provider,
    "communauto": communauto.provider,
}

NETWORK_NAMES = tuple(_FACTORIES)

# Bike-share networks (the "vélo" side of a display mode).
BIKE_NETWORKS = ("bixi", "avelo")

# Display modes (the integration options shown on the module):
#   "velo"            -> the configured bike network only
#   "velo_communauto" -> alternate bike network and Communauto every rotate_seconds
#   "communauto"      -> Communauto only
MODES = ("velo", "velo_communauto", "communauto")


def active_networks(mode: str, bike_network: str) -> list[str]:
    """The ordered list of networks a mode cycles through."""
    bike = bike_network if bike_network in BIKE_NETWORKS else "avelo"
    if mode == "communauto":
        return ["communauto"]
    if mode == "velo_communauto":
        return [bike, "communauto"]
    return [bike]  # "velo"


def get_provider(network: str) -> Provider:
    try:
        factory = _FACTORIES[network]
    except KeyError:
        raise ValueError(
            f"Unknown network {network!r}. Choose one of: {', '.join(NETWORK_NAMES)}"
        ) from None
    return factory()
