"""BIXI Montréal — GBFS v2, mixed mechanical + electric fleet."""

from __future__ import annotations

from .base import Column
from .gbfs import BikeShareProvider

# Column layout: (key, color, number right-edge x exclusive, icon center x).
# BIXI has both mechanical and electric bikes, so it shows three columns.
COLUMNS = [
    Column("bike", (76, 235, 115), 44, 40, icon="bike"),
    Column("bolt", (255, 224, 64), 54, 51, icon="bolt"),
    Column("park", (96, 184, 255), 64, 60, icon="P"),
]


def provider() -> BikeShareProvider:
    return BikeShareProvider(
        name="bixi",
        display_name="BIXI",
        information_url="https://gbfs.velobixi.com/gbfs/en/station_information.json",
        status_url="https://gbfs.velobixi.com/gbfs/en/station_status.json",
        columns=COLUMNS,
        name_max_width=36,
        logo_filename="bixi_logo_27.png",
        fallback_text="BIXI",
    )
