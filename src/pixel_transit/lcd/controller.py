"""Run the LCD mode-selection menu on the Waveshare 1.3" HAT.

Wires the hardware (ST7789 display + buttons) to the pure :class:`Menu` model and
persists the chosen mode to the configuration. Controls:

* Joystick up/down : move the highlight
* Joystick press   : validate the highlighted mode
* KEY1 / KEY2 / KEY3 : jump to and validate option 1 / 2 / 3 directly

NOTE: this is prepared but intentionally NOT wired into the display daemon yet.
Run it standalone with ``python -m pixel_transit.lcd``.
"""

from __future__ import annotations

import logging
import time

from ..config import load_config, save_config
from .menu import Menu

REFRESH_SECONDS = 0.05
CONFIRM_SECONDS = 1.5


def _apply_mode(mode: str) -> None:
    config = load_config()
    config["mode"] = mode
    save_config(config)
    logging.info("LCD menu: mode set to %s", mode)


def run_menu() -> None:
    from .buttons import Buttons  # noqa: PLC0415 — lazy, Pi-only
    from .st7789 import ST7789  # noqa: PLC0415 — lazy, Pi-only

    display = ST7789()
    buttons = Buttons()

    try:
        active = load_config().get("mode")
    except Exception:
        active = None
    menu = Menu(active_key=active)
    display.display(menu.render())

    try:
        while True:
            confirmed_mode: str | None = None
            for event in buttons.poll():
                if event in ("up", "left"):
                    menu.move(-1)
                elif event in ("down", "right"):
                    menu.move(1)
                elif event == "press":
                    confirmed_mode = menu.current_key
                elif event in ("key1", "key2", "key3"):
                    menu.select_index(int(event[-1]) - 1)
                    confirmed_mode = menu.current_key

            if confirmed_mode is not None:
                _apply_mode(confirmed_mode)
                menu.active_key = confirmed_mode
                display.display(menu.render(confirmed=True))
                time.sleep(CONFIRM_SECONDS)

            display.display(menu.render())
            time.sleep(REFRESH_SECONDS)
    except KeyboardInterrupt:
        pass
    finally:
        display.close()
        buttons.cleanup()
