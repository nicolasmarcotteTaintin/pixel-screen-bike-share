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
    parser.add_argument("--screen",
                        choices=("language", "main", "mode", "brightness", "sleep", "rotate", "info"),
                        default="main", help="Which screen to preview (default: main).")
    parser.add_argument("--lang", default="fr", help="Language for the preview (fr/en).")
    parser.add_argument("--selected", type=int, default=0, help="Highlighted row for list screens.")
    parser.add_argument("--active", type=str, default=None, help="Active key marked in the preview.")
    parser.add_argument("--value", type=int, default=80, help="Value for the brightness preview.")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    if args.preview:
        from .menu import (
            BrightnessScreen,
            info_screen,
            language_menu,
            main_menu,
            mode_menu,
            rotate_menu,
            sleep_screen,
        )

        if args.screen == "language":
            screen = language_menu(active_key=args.active or args.lang)
        elif args.screen == "main":
            # --active sets the current mode (so "Alternance" shows enabled/disabled).
            screen = main_menu(args.lang, selected=args.selected, mode=args.active)
        elif args.screen == "brightness":
            screen = BrightnessScreen(args.value, lang=args.lang)
        elif args.screen == "sleep":
            screen = sleep_screen(args.lang, enabled=True, off_start="21:00", off_end="08:00")
        elif args.screen == "rotate":
            screen = rotate_menu(args.lang, active_seconds=args.value)
        elif args.screen == "info":
            screen = info_screen(args.lang, {
                "host": "bixi-pixoo", "ip": "192.168.50.156", "ssid": "MonReseau",
                "mode": "Vélo+Comm.", "network": "avelo",
                "pixoo": "192.168.50.132", "brightness": "35%",
            })
        else:
            screen = mode_menu(args.lang, active_key=args.active)
        if hasattr(screen, "select_index"):
            screen.select_index(args.selected)
        screen.render().save(args.preview)
        print(f"Menu preview ({args.screen}) written to {args.preview}")
        return 0

    from .controller import run_menu

    run_menu()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
