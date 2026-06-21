"""Entry point: ``python -m pixel_transit.lcd``.

Without arguments, runs the interactive menus on the LCD HAT (Raspberry Pi only).
With ``--preview PATH``, renders a menu to a PNG so it can be checked without any
hardware.
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="LCD language + mode menus (1.3\" ST7789 240x240).")
    parser.add_argument("--preview", type=Path, help="Render a menu to a PNG and exit (no hardware).")
    parser.add_argument("--screen", choices=("language", "mode"), default="mode",
                        help="Which screen to preview (default: mode).")
    parser.add_argument("--lang", default="fr", help="Language for the mode preview (fr/en).")
    parser.add_argument("--selected", type=int, default=0, help="Highlighted row for the preview.")
    parser.add_argument("--active", type=str, default=None, help="Active key marked in the preview.")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    if args.preview:
        from .menu import language_menu, mode_menu

        if args.screen == "language":
            menu = language_menu(active_key=args.active or args.lang)
        else:
            menu = mode_menu(args.lang, active_key=args.active)
        menu.select_index(args.selected)
        menu.render().save(args.preview)
        print(f"Menu preview ({args.screen}) written to {args.preview}")
        return 0

    from .controller import run_menu

    run_menu()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
