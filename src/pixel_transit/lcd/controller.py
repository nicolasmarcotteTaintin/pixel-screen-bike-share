"""Run the LCD menus on the Waveshare 1.3" HAT.

Flow:

1. Language  : Français / English            -> config ``"language"``
2. Settings menu :
       * Mode d'affichage -> mode screen        -> config ``"mode"``
       * Alternance       -> rotation interval   -> config ``"rotate_seconds"``
                             (disabled unless mode == "velo_communauto")
       * Luminosité écran -> Pixoo brightness    -> config ``"brightness"``
       * Luminosité Pi    -> LCD backlight (PWM) -> config ``"lcd_brightness"``
       * Veille du soir   -> evening-off editor  -> config ``"off_*"``
       * Langue           -> back to language screen
       * Information      -> read-only device info
       * Éteindre l'écran -> turn the LCD off (wake on any button)

Controls:

* Joystick up/down     : move the highlight (list screens only)
* Joystick left/right  : adjust brightness (hold to ramp); the sleep editor uses them too
* Joystick press / KEY1: validate / open
* KEY2                 : disabled (does nothing)
* KEY3                 : back one level (submenu -> settings); turns the screen off at the top

The screen also turns itself off after ``IDLE_OFF_SECONDS`` without input.

NOTE: prepared but intentionally NOT wired into the display daemon yet.
Run it standalone with ``python -m pixel_transit.lcd``.
"""

from __future__ import annotations

import logging
import socket
import time

from ..config import load_config, save_config
from ..sun import montreal_sunset_minutes
from ..wifi import get_wifi_ssid
from .menu import (
    BRIGHTNESS_TITLES,
    ROTATE_STRINGS,
    BrightnessScreen,
    info_screen,
    language_menu,
    main_menu,
    minutes_to_hhmm,
    mode_menu,
    rotate_screen,
    sleep_screen,
)

POLL_SECONDS = 0.05
CONFIRM_SECONDS = 1.2
IDLE_OFF_SECONDS = 30.0
# Long-press: hold the joystick to ramp a brightness value continuously.
REPEAT_DELAY_SECONDS = 0.4      # hold this long before auto-repeat starts
REPEAT_INTERVAL_SECONDS = 0.08  # step cadence while held

# Screens opened from the settings menu; KEY3 backs out of these to the menu
# (rather than turning the screen off, which it does at the top level).
SUBMENUS = frozenset({"mode", "rotate", "brightness", "lcd_brightness", "sleep", "info"})


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
    display.set_brightness(config.get("lcd_brightness", 100))

    state = "language"
    screen = language_menu(active_key=lang)
    display.display(screen.render())
    last_activity = time.monotonic()
    held_dir = 0
    held_since = 0.0
    last_repeat = 0.0

    try:
        while True:
            events = buttons.poll()

            # Screen off (via "Éteindre l'écran", KEY3, or idle): stay dark until
            # any button wakes it back to the settings menu.
            if state == "off":
                if events:
                    display.set_backlight(True)
                    state, screen = "main", _main_menu()
                    display.display(screen.render())
                    last_activity = time.monotonic()
                time.sleep(POLL_SECONDS)
                continue

            if events:
                last_activity = time.monotonic()

            confirmed = False
            key3 = False
            for raw in events:
                if raw == "key2":
                    continue  # centre key: disabled
                if raw == "key3":
                    key3 = True  # last key: back one level, or turn off at the top
                    break
                event = "press" if raw == "key1" else raw  # first key = joystick click

                if state in ("brightness", "lcd_brightness", "rotate"):
                    # Brightness / alternation: left/right only (hold to ramp).
                    if event == "left":
                        screen.adjust(-1)
                    elif event == "right":
                        screen.adjust(1)
                    elif event == "press":
                        confirmed = True
                    if state == "lcd_brightness" and event in ("left", "right"):
                        display.set_brightness(screen.value)  # live preview on the LCD
                elif state == "sleep":
                    if event == "up":
                        screen.move(-1)
                    elif event == "down":
                        screen.move(1)
                    elif event == "left":
                        screen.adjust(-1)
                    elif event == "right":
                        screen.adjust(1)
                    elif event == "press":
                        confirmed = True
                elif state == "info":
                    confirmed = True  # read-only: any button returns to the menu
                else:  # list screens (language, main, mode): up/down only
                    if event == "up":
                        screen.move(-1)
                    elif event == "down":
                        screen.move(1)
                    elif event == "press":
                        confirmed = True

            if key3:
                if state in SUBMENUS:
                    if state == "lcd_brightness":
                        display.set_brightness(load_config().get("lcd_brightness", 100))  # revert live preview
                    state, screen = "main", _main_menu()
                    display.display(screen.render())
                    last_activity = time.monotonic()
                else:  # main / language: exit — turn the screen off
                    display.set_backlight(False)
                    state = "off"
                time.sleep(POLL_SECONDS)
                continue

            need_render = bool(events)  # only redraw when something changed (menus are static)

            # Long-press: hold left/right on a brightness/alternation screen to ramp.
            if state in ("brightness", "lcd_brightness", "rotate"):
                held = buttons.pressed()
                direction = 1 if "right" in held else -1 if "left" in held else 0
                now = time.monotonic()
                if direction == 0:
                    held_dir = 0
                elif direction != held_dir:
                    held_dir, held_since, last_repeat = direction, now, now  # initial step already applied
                elif now - held_since >= REPEAT_DELAY_SECONDS and now - last_repeat >= REPEAT_INTERVAL_SECONDS:
                    screen.adjust(direction)
                    if state == "lcd_brightness":
                        display.set_brightness(screen.value)
                    last_repeat = now
                    last_activity = now
                    need_render = True
            else:
                held_dir = 0

            if confirmed:
                state, screen = _confirm(state, screen, display)
                if state == "off":  # "Éteindre l'écran" selected
                    time.sleep(POLL_SECONDS)
                    continue
                need_render = True

            # Idle: turn the panel off when the menu is left untouched.
            if time.monotonic() - last_activity > IDLE_OFF_SECONDS:
                display.set_backlight(False)
                state = "off"
                time.sleep(POLL_SECONDS)
                continue

            if need_render:
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
        return "main", _main_menu()

    if state == "main":
        lang = _current_lang()
        choice = screen.current_key
        config = load_config()
        if choice == "mode":
            return "mode", mode_menu(lang, active_key=config.get("mode"))
        if choice == "rotate":
            if config.get("mode") != "velo_communauto":
                _flash_footer(display, _main_menu(), _rotate_hint(lang))
                return "main", _main_menu()
            return "rotate", rotate_screen(lang, config.get("rotate_seconds", 10))
        if choice == "brightness":
            return "brightness", BrightnessScreen(
                config.get("brightness", 80), lang=lang, title=_brightness_title("screen", lang))
        if choice == "lcd_brightness":
            return "lcd_brightness", BrightnessScreen(
                config.get("lcd_brightness", 100), lang=lang, title=_brightness_title("pi", lang))
        if choice == "sleep":
            return "sleep", sleep_screen(
                lang,
                enabled=config.get("off_enabled", True),
                off_start=config.get("off_start", "21:00"),
                off_end=config.get("off_end", "08:00"),
                sunset_label=_sunset_label(),
            )
        if choice == "info":
            return "info", info_screen(lang, _gather_info(config))
        if choice == "exit":
            display.set_backlight(False)
            return "off", screen
        return "language", language_menu(active_key=lang)

    if state == "mode":
        _save("mode", screen.current_key)
        _flash(display, screen)
        return "main", _main_menu()

    if state == "rotate":
        _save("rotate_seconds", screen.value)
        _flash(display, screen)
        return "main", _main_menu()

    if state == "brightness":
        _save("brightness", screen.value)
        _flash(display, screen)
        return "main", _main_menu()

    if state == "lcd_brightness":
        _save("lcd_brightness", screen.value)  # backlight already applied live
        _flash(display, screen)
        return "main", _main_menu()

    if state == "sleep":
        config = load_config()
        config["off_enabled"] = screen.enabled
        config["off_start"] = "sunset" if screen.sunset else minutes_to_hhmm(screen.off_minutes)
        config["off_end"] = minutes_to_hhmm(screen.on_minutes)
        save_config(config)
        logging.info("LCD menu: evening-off enabled=%s %s-%s",
                     screen.enabled, config["off_start"], config["off_end"])
        _flash(display, screen)
        return "main", _main_menu()

    if state == "info":
        return "main", _main_menu()

    return state, screen


def _main_menu():
    config = load_config()
    return main_menu(config.get("language", "fr"), mode=config.get("mode"))


def _current_lang() -> str:
    try:
        return load_config().get("language", "fr")
    except Exception:
        return "fr"


def _brightness_title(kind: str, lang: str) -> str:
    titles = BRIGHTNESS_TITLES.get(kind, {})
    return titles.get(lang, titles.get("fr", ""))


def _rotate_hint(lang: str) -> str:
    return ROTATE_STRINGS.get(lang, ROTATE_STRINGS["fr"])["disabled_hint"]


def _sunset_label() -> str:
    """Approximate today's Montréal sunset, e.g. ``"≈20:15"`` (for the sleep screen)."""
    minutes = montreal_sunset_minutes()
    return "≈" + minutes_to_hhmm(minutes) if minutes is not None else "—"


def _flash_footer(display, menu, message: str) -> None:
    """Briefly show ``message`` in the menu footer (e.g. a disabled-option hint)."""
    menu.confirmed_footer = message
    display.display(menu.render(confirmed=True))
    time.sleep(CONFIRM_SECONDS)


_MODE_SHORT = {"velo": "Vélo", "velo_communauto": "Vélo+Comm.", "communauto": "Communauto"}


def _gather_info(config) -> dict:
    mode = config.get("mode", "—")
    return {
        "host": socket.gethostname(),
        "ip": _local_ip(),
        "ssid": get_wifi_ssid() or "—",
        "mode": _MODE_SHORT.get(mode, mode),
        "network": config.get("network", "—"),
        "pixoo": config.get("pixoo_ip") or "auto",
        "brightness": f"{config.get('brightness', 80)}%",
    }


def _local_ip() -> str:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]
        finally:
            sock.close()
    except OSError:
        return "—"


def _flash(display, screen) -> None:
    display.display(screen.render(confirmed=True))
    time.sleep(CONFIRM_SECONDS)
