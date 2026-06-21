"""Run the LCD menus on the Waveshare 1.3" HAT.

Two screens, in order:

1. Language  : Français / English  -> saved to config ``"language"``
2. Display mode (in that language) -> saved to config ``"mode"``

Controls:

* Joystick up/down : move the highlight
* Joystick press   : validate the highlighted row
* KEY1 / KEY2 / KEY3 : jump to and validate row 1 / 2 / 3 directly
* Joystick left    : on the mode screen, go back to the language screen

NOTE: prepared but intentionally NOT wired into the display daemon yet.
Run it standalone with ``python -m pixel_transit.lcd``.
"""

from __future__ import annotations

import logging
import time

from ..config import load_config, save_config
from .menu import language_menu, mode_menu

POLL_SECONDS = 0.05
CONFIRM_SECONDS = 1.5


def _save(key: str, value: str) -> None:
    config = load_config()
    config[key] = value
    save_config(config)
    logging.info("LCD menu: %s set to %s", key, value)


def run_menu() -> None:
    from .buttons import Buttons  # noqa: PLC0415 — lazy, Pi-only
    from .st7789 import ST7789  # noqa: PLC0415 — lazy, Pi-only

    display = ST7789()
    buttons = Buttons()

    try:
        config = load_config()
        lang = config.get("language", "fr")
        active_mode = config.get("mode")

        state = "language"
        menu = language_menu(active_key=lang)
        display.display(menu.render())

        while True:
            confirmed = False
            go_back = False
            for event in buttons.poll():
                if event in ("up", "left") and state == "language":
                    menu.move(-1)
                elif event == "up":
                    menu.move(-1)
                elif event in ("down", "right"):
                    menu.move(1)
                elif event == "left" and state == "mode":
                    go_back = True
                elif event == "press":
                    confirmed = True
                elif event in ("key1", "key2", "key3"):
                    menu.select_index(int(event[-1]) - 1)
                    confirmed = True

            if go_back:
                state = "language"
                menu = language_menu(active_key=lang)
            elif confirmed and state == "language":
                lang = menu.current_key
                _save("language", lang)
                display.display(menu.render(confirmed=True))
                time.sleep(CONFIRM_SECONDS)
                state = "mode"
                menu = mode_menu(lang, active_key=active_mode)
            elif confirmed and state == "mode":
                active_mode = menu.current_key
                _save("mode", active_mode)
                menu.active_key = active_mode
                display.display(menu.render(confirmed=True))
                time.sleep(CONFIRM_SECONDS)

            display.display(menu.render())
            time.sleep(POLL_SECONDS)
    except KeyboardInterrupt:
        pass
    finally:
        display.close()
        buttons.cleanup()
