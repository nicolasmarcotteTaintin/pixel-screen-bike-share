"""àVélo (Québec City, RTC) — GBFS v3, all-electric PBSC network.

Because every àVélo bike is electric there is no separate e-bike column: the
single bike column is the total available, freeing width for longer names.
"""

from __future__ import annotations

from .base import Column
from .gbfs import BikeShareProvider

# All-electric fleet: just bikes + docks. The park column ends at 64 so its last
# pixel is column 63 (full width, no right margin).
COLUMNS = [
    Column("bike", (76, 235, 115), 54, 49, icon="bike"),
    Column("park", (96, 184, 255), 64, 59, icon="P"),
]


def provider() -> BikeShareProvider:
    return BikeShareProvider(
        name="avelo",
        display_name="àVélo",
        information_url="https://quebec.publicbikesystem.net/customer/gbfs/v3.0/station_information",
        status_url="https://quebec.publicbikesystem.net/customer/gbfs/v3.0/station_status",
        columns=COLUMNS,
        name_max_width=44,
        logo_filename="avelo_logo_27.png",
        fallback_text="AVELO",
    )
