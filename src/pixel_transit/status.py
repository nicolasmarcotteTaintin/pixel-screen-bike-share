"""Writes a one-glance health snapshot for quick diagnosis (``cat status.json``)."""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Any

from .config import BASE_DIR

STATUS_PATH = Path(
    os.getenv("PIXEL_TRANSIT_STATUS_PATH")
    or os.getenv("BIXI_STATUS_PATH")
    or (BASE_DIR / "status.json")
)


def write_status(**fields: Any) -> None:
    fields["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    try:
        STATUS_PATH.write_text(json.dumps(fields, indent=2) + "\n", encoding="utf-8")
    except OSError as exc:
        logging.debug("Could not write status file %s: %s", STATUS_PATH, exc)
