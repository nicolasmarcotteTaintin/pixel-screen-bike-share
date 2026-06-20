"""Renders a car-share network (Communauto) as a nearest-cars list.

Each row is one available car: a kind marker (F = FLEX free-floating,
S = station round-trip), a location label (station name, or "FLEX"), an optional
compass arrow pointing from home toward a free-floating car, and the distance.
The header band summarises how many of each are available nearby.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

from ..geo import format_distance
from ..providers.base import CarRow, CarShareView
from .common import CANVAS_SIZE, HEADER_BG, ROW_BG, draw_top_bar
from .fonts import (
    FONT_4X6_HEIGHT,
    FONT_5X7_HEIGHT,
    clip_text,
    draw_small_text,
    draw_tiny_text,
    small_text_width,
    tiny_text_width,
)
from .icons import draw_arrow, draw_car_icon

CONTENT_TOP = 12
ROW_HEIGHT = 3 + FONT_4X6_HEIGHT + 3

FLEX_COLOR = (76, 235, 115)
STATION_COLOR = (96, 184, 255)


def _kind_color(kind: str) -> tuple[int, int, int]:
    return FLEX_COLOR if kind == "flex" else STATION_COLOR


def render(view: CarShareView, logo_path: Path | None, fallback_text: str) -> Image.Image:
    image = Image.new("RGB", (CANVAS_SIZE, CANVAS_SIZE), "black")
    draw = ImageDraw.Draw(image)

    rows = view.rows[:3]
    rows_top = 64 - len(rows) * ROW_HEIGHT if rows else CONTENT_TOP + 11
    header_bottom = rows_top

    draw.rectangle((0, CONTENT_TOP + 5, 63, header_bottom - 1), fill=HEADER_BG)
    _draw_header(draw, view, header_bottom)

    if not rows:
        no_data = "NO CAR"
        x = max(0, (64 - small_text_width(no_data)) // 2)
        y = header_bottom + max(0, (64 - header_bottom - FONT_5X7_HEIGHT) // 2)
        draw_small_text(draw, x, y, no_data, (255, 80, 80))
        draw_top_bar(image, draw, logo_path, fallback_text)
        return image

    for index, row in enumerate(rows):
        y = rows_top + index * ROW_HEIGHT
        draw.rectangle((0, y, 63, y + ROW_HEIGHT - 1), fill=ROW_BG[index % len(ROW_BG)])
        _draw_row(draw, row, y)

    draw_top_bar(image, draw, logo_path, fallback_text)
    return image


def _draw_header(draw: ImageDraw.ImageDraw, view: CarShareView, header_bottom: int) -> None:
    """Summary counts inside the header band: green FLEX total, blue station total."""
    y = CONTENT_TOP + 7
    if header_bottom <= y + FONT_4X6_HEIGHT:
        return
    draw_tiny_text(draw, 1, y, f"F{min(99, view.flex_count)}", FLEX_COLOR)
    station_text = f"S{min(99, view.station_count)}"
    draw_tiny_text(draw, 63 - tiny_text_width(station_text), y, station_text, STATION_COLOR)


def _draw_row(draw: ImageDraw.ImageDraw, row: CarRow, y: int) -> None:
    color = _kind_color(row.kind)
    text_y = y + max(0, (ROW_HEIGHT - FONT_4X6_HEIGHT) // 2)

    # Left: kind marker (F / S).
    marker = "F" if row.kind == "flex" else "S"
    draw_tiny_text(draw, 0, text_y, marker, color)
    label_x = tiny_text_width(marker) + 2

    # Right: distance, right-aligned to the edge.
    distance = format_distance(row.distance_m)
    distance_w = tiny_text_width(distance)
    distance_x = 64 - distance_w
    draw_tiny_text(draw, distance_x, text_y, distance, (210, 210, 210))

    # Compass arrow just left of the distance — only for free-floating cars, whose
    # "location" is a direction from home. Station rows show their name instead.
    right_limit = distance_x - 1
    if row.kind == "flex" and row.direction:
        arrow_w = draw_arrow(draw, right_limit - 4, text_y + 1, row.direction, color)
        if arrow_w:
            right_limit -= arrow_w + 1

    # Middle: location label, clipped to the remaining width.
    max_width = max(0, right_limit - label_x - 1)
    label = clip_text(row.label.upper(), max_width)
    draw_tiny_text(draw, label_x, text_y, label, (235, 235, 235))
