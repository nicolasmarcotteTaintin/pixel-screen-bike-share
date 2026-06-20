"""Shared canvas constants and the top bar (logo + clock) used by every view."""

from __future__ import annotations

import logging
import time
from pathlib import Path

from PIL import Image, ImageDraw

from .fonts import draw_pixel_text, draw_small_text, pixel_text_width

CANVAS_SIZE = 64

# Colour palette shared by the table views.
HEADER_BG = (34, 78, 120)
ROW_BG = [(50, 50, 56), (18, 18, 20)]
CLOCK_COLOR = (210, 210, 210)

# Slightly different name tint per row to tell them apart.
NAME_TINTS = [
    (255, 255, 255),
    (200, 224, 255),
    (255, 224, 200),
]

_LOGO_CACHE: dict[str, Image.Image | None] = {}


def load_logo(logo_path: Path | None) -> Image.Image | None:
    """Load (and cache) an RGBA logo image, or None if unavailable."""
    if logo_path is None:
        return None
    key = str(logo_path)
    if key not in _LOGO_CACHE:
        try:
            _LOGO_CACHE[key] = Image.open(logo_path).convert("RGBA")
        except OSError:
            logging.warning("Logo image %s unavailable, falling back to text logo", logo_path)
            _LOGO_CACHE[key] = None
    return _LOGO_CACHE[key]


def draw_clock(draw: ImageDraw.ImageDraw, x: int, y: int) -> None:
    from .fonts import FONT_5X7_WIDTH

    now = time.localtime()
    hours = f"{now.tm_hour:02d}"
    minutes = f"{now.tm_min:02d}"

    draw_small_text(draw, x, y, hours, CLOCK_COLOR)
    # 1px-wide colon with a single free column on each side, toggling every second.
    colon_x = x + len(hours) * (FONT_5X7_WIDTH + 1)
    if int(time.time()) % 2 == 0:
        draw.point((colon_x, y + 2), fill=CLOCK_COLOR)
        draw.point((colon_x, y + 4), fill=CLOCK_COLOR)
    draw_small_text(draw, colon_x + 2, y, minutes, CLOCK_COLOR)


def draw_top_bar(
    image: Image.Image,
    draw: ImageDraw.ImageDraw,
    logo_path: Path | None,
    fallback_text: str,
) -> None:
    """Draw the logo (or a text fallback) at top-left and the clock to its right."""
    logo = load_logo(logo_path)
    if logo is not None:
        logo_x = 1
        image.paste(logo, (logo_x, 0), logo)
        logo_right = logo_x + logo.width
    else:
        draw_pixel_text(draw, 0, 0, fallback_text, (245, 245, 245), scale=2)
        logo_right = pixel_text_width(fallback_text, scale=2)

    # Clock to the right of the logo, in the clear strip above the header band.
    draw_clock(draw, logo_right + 10, 3)
