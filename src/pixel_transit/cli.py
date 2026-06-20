"""Command-line entry point and logging setup."""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

from .app import register_signal_handlers, run_display_loop
from .config import BASE_DIR, ensure_config_exists
from .setup_server import run_setup_server

LOG_PATH = Path(
    os.getenv("PIXEL_TRANSIT_LOG_PATH")
    or os.getenv("BIXI_LOG_PATH")
    or "/var/log/pixel-transit.log"
)


def setup_logging() -> None:
    handlers: list[logging.Handler] = [logging.StreamHandler()]
    try:
        handlers.append(logging.FileHandler(LOG_PATH))
    except OSError as exc:
        fallback = BASE_DIR / "pixel-transit.log"
        handlers.append(logging.FileHandler(fallback))
        print(f"Could not write {LOG_PATH}: {exc}. Logging to {fallback}", file=sys.stderr)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=handlers,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Display live transit status (BIXI, àVélo, Communauto) on a Pixoo 64."
    )
    parser.add_argument("--setup", action="store_true", help="Run the local Flask setup server.")
    parser.add_argument("--once", action="store_true", help="Render and send one frame, then exit.")
    parser.add_argument("--preview", type=Path, help="Write the rendered 64x64 image to this PNG path.")
    args = parser.parse_args()

    setup_logging()
    ensure_config_exists()

    if args.setup:
        run_setup_server()
        return 0

    register_signal_handlers()
    run_display_loop(once=args.once, preview_path=args.preview)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
