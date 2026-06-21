"""Entry point: ``python -m pixel_transit.lcd``.

Without arguments, runs the interactive menu on the LCD HAT (Raspberry Pi only).
With ``--preview PATH``, renders the menu to a PNG so it can be checked without
any hardware.
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="LCD mode-selection menu (1.3\" ST7789 240x240).")
    parser.add_argument("--preview", type=Path, help="Render the menu to a PNG and exit (no hardware).")
    parser.add_argument("--selected", type=int, default=0, help="Highlighted row for the preview (0-2).")
    parser.add_argument("--active", type=str, default=None, help="Active mode marked in the preview.")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    if args.preview:
        from .menu import Menu

        menu = Menu(selected=max(0, min(2, args.selected)), active_key=args.active)
        menu.render().save(args.preview)
        print(f"Menu preview written to {args.preview}")
        return 0

    from .controller import run_menu

    run_menu()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
