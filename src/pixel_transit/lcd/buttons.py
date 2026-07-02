"""GPIO buttons of the Waveshare 1.3" LCD HAT (joystick + 3 keys).

Active-low inputs with internal pull-ups. ``RPi.GPIO`` is imported lazily so this
module loads anywhere; only :meth:`Buttons.__init__` needs a Raspberry Pi.
"""

from __future__ import annotations

# BCM pin map for the Waveshare 1.3inch LCD HAT.
PINS = {
    "up": 6,
    "down": 19,
    "left": 5,
    "right": 26,
    "press": 13,
    "key1": 21,
    "key2": 20,
    "key3": 16,
}


class Buttons:
    def __init__(self) -> None:
        import RPi.GPIO as GPIO  # noqa: PLC0415 — lazy, Pi-only

        self._gpio = GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        for pin in PINS.values():
            GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        self._was_pressed = {name: False for name in PINS}

    def poll(self) -> list[str]:
        """Return the names of buttons newly pressed since the last poll (edge-triggered)."""
        events: list[str] = []
        for name, pin in PINS.items():
            pressed = self._gpio.input(pin) == 0  # active-low
            if pressed and not self._was_pressed[name]:
                events.append(name)
            self._was_pressed[name] = pressed
        return events

    def pressed(self) -> set[str]:
        """Return the names of buttons currently held down (level, not edge)."""
        return {name for name, pin in PINS.items() if self._gpio.input(pin) == 0}

    def cleanup(self) -> None:
        self._gpio.cleanup(list(PINS.values()))
