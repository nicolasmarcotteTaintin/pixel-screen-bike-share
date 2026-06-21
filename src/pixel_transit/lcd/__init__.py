"""1.3" 240x240 IPS LCD (ST7789) mode-selection menu.

Prepared but not yet integrated into the display daemon. Pure menu logic lives in
:mod:`pixel_transit.lcd.menu`; hardware glue in :mod:`pixel_transit.lcd.st7789`,
:mod:`pixel_transit.lcd.buttons` and :mod:`pixel_transit.lcd.controller`.
"""

from __future__ import annotations

from .menu import MENU_OPTIONS, Menu

__all__ = ["Menu", "MENU_OPTIONS"]
