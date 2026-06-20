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


def get_provider(network: str) -> Provider:
    try:
        factory = _FACTORIES[network]
    except KeyError:
        raise ValueError(
            f"Unknown network {network!r}. Choose one of: {', '.join(NETWORK_NAMES)}"
        ) from None
    return factory()
