"""Provider interface and the view models passed to the renderers.

A *provider* knows how to fetch live data for one transit network and turn it
into a view model. The app loop is provider-agnostic: it calls ``fetch`` and
hands the result to the renderer selected by ``kind``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"


# --- Bike-share view model ---------------------------------------------------

@dataclass(frozen=True)
class Column:
    """One numeric column in a bike-share table.

    ``right`` is the exclusive right edge x for right-aligned multi-digit values;
    ``center_x`` is where a single digit (and the header icon) is centred.
    ``icon`` is one of ``"bike"``, ``"bolt"`` or a literal header label like ``"P"``.
    """

    key: str
    color: tuple[int, int, int]
    right: int
    center_x: int
    icon: str


@dataclass
class StationRow:
    name: str
    values: list[int]


@dataclass
class BikeShareView:
    columns: list[Column]
    rows: list[StationRow]
    name_max_width: int


# --- Car-share view model ----------------------------------------------------

@dataclass
class CarRow:
    """One available car, located relative to the configured home point."""

    label: str            # station name, or a short service tag for free-floating
    distance_m: float
    kind: str             # "flex" (free-floating) or "station" (round-trip)
    direction: str = ""   # 8-point compass direction from home (free-floating)


@dataclass
class CarShareView:
    rows: list[CarRow]
    flex_count: int = 0
    station_count: int = 0


# --- Provider protocol -------------------------------------------------------

@runtime_checkable
class Provider(Protocol):
    name: str
    display_name: str
    fallback_text: str   # text logo drawn when the PNG logo is missing
    logo_filename: str   # file under assets/, or "" for no logo
    kind: str            # "bikeshare" | "carshare"

    def fetch(self, config: dict[str, Any]) -> Any:
        """Return a view model (BikeShareView or CarShareView) for this network."""
        ...


def logo_path(filename: str) -> Path | None:
    return ASSETS_DIR / filename if filename else None
