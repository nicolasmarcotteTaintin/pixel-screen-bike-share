"""Run the LCD menus on the Waveshare 1.3" HAT.

Flow:

1. Language  : Français / English            -> config ``"language"``
2. Settings menu : Mode / Luminosité / Langue
       * Mode        -> mode screen           -> config ``"mode"``
       * Luminosité  -> brightness slider     -> config ``"brightness"``
       * Langue      -> back to the language screen

Controls:

* Joystick up/down   : move the highlight (list screens)
* Joystick left/right: adjust the value (brightness screen)
* Joystick press     : validate / open
* KEY1 / KEY2 / KEY3 : jump to row 1 / 2 / 3 on list screens

NOTE: prepared but intentionally NOT wired into the display daemon yet.
Run it standalone with ``python -m pixel_transit.lcd``.
"""

from __future__ import annotations

import logging
import time

from ..config import load_config, save_config
from .menu import BrightnessScreen, language_menu, main_menu, mode_menu

POLL_SECONDS = 0.05
CONFIRM_SECONDS = 1.2


def _save(key: str, value) -> None:
    config = load_config()
    config[key] = value
    save_config(config)
    logging.info("LCD menu: %s set to %s", key, value)


def run_menu() -> None:
    from .buttons import Buttons  # noqa: PLC0415 — lazy, Pi-only
    from .st7789 import ST7789  # noqa: PLC0415 — lazy, Pi-only

    display = ST7789()
    buttons = Buttons()

    config = load_config()
    lang = config.get("language", "fr")
    active_mode = config.get("mode")
    brightness = config.get("brightness", 80)

    state = "language"
    screen = language_menu(active_key=lang)
    display.display(screen.render())

    try:
        while True:
            confirmed = False
            for event in buttons.poll():
                if state == "brightness":
                    if event in ("left", "down"):
                        screen.adjust(-1)
                    elif event in ("right", "up"):
                        screen.adjust(1)
                    elif event == "press":
                        confirmed = True
                else:  # list screens
                    if event in ("up", "left"):
                        screen.move(-1)
                    elif event in ("down", "right"):
                        screen.move(1)
                    elif event == "press":
                        confirmed = True
                    elif event in ("key1", "key2", "key3"):
                        screen.select_index(int(event[-1]) - 1)
                        confirmed = True

            if confirmed:
                state, screen = _confirm(state, screen, display)

            display.display(screen.render())
            time.sleep(POLL_SECONDS)
    except KeyboardInterrupt:
        pass
    finally:
        display.close()
        buttons.cleanup()


def _confirm(state, screen, display):
    """Handle a validation on the current screen; return the next (state, screen)."""
    if state == "language":
        lang = screen.current_key
        _save("language", lang)
        _flash(display, screen)
        return "main", main_menu(lang)

    if state == "main":
        lang = _current_lang()
        choice = screen.current_key
        if choice == "mode":
            return "mode", mode_menu(lang, active_key=load_config().get("mode"))
        if choice == "brightness":
            return "brightness", BrightnessScreen(load_config().get("brightness", 80), lang=lang)
        return "language", language_menu(active_key=lang)

    if state == "mode":
        _save("mode", screen.current_key)
        _flash(display, screen)
        return "main", main_menu(_current_lang())

    if state == "brightness":
        _save("brightness", screen.value)
        _flash(display, screen)
        return "main", main_menu(_current_lang())

    return state, screen


def _current_lang() -> str:
    try:
        return load_config().get("language", "fr")
    except Exception:
        return "fr"


def _flash(display, screen) -> None:
    display.display(screen.render(confirmed=True))
    time.sleep(CONFIRM_SECONDS)
