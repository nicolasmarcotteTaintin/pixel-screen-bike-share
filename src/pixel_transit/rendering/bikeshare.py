"""Renders a bike-share network as an Excel-style table on the 64x64 canvas."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

from ..providers.base import BikeShareView, Column, StationRow
from .common import (
    CANVAS_SIZE,
    HEADER_BG,
    NAME_TINTS,
    ROW_BG,
    draw_top_bar,
)
from .fonts import (
    FONT_4X6_HEIGHT,
    clip_text,
    draw_station_name,
    draw_tiny_text,
    draw_small_text,
    small_text_width,
    tiny_text_width,
)
from .icons import draw_bike_icon, draw_bolt_icon

CONTENT_TOP = 12
ROW_HEIGHT = 3 + FONT_4X6_HEIGHT + 3  # 3px above text + 6px text + 3px below


def render(view: BikeShareView, logo_path: Path | None, fallback_text: str) -> Image.Image:
    image = Image.new("RGB", (CANVAS_SIZE, CANVAS_SIZE), "black")
    draw = ImageDraw.Draw(image)

    rows = view.rows[:3]
    # Rows anchored to the bottom edge; the header band absorbs the extra space.
    rows_top = 64 - len(rows) * ROW_HEIGHT if rows else CONTENT_TOP + 11
    header_bottom = rows_top

    # Header band (column icons). The square logo overlaps its left side.
    draw.rectangle((0, CONTENT_TOP + 5, 63, header_bottom - 1), fill=HEADER_BG)

    if not rows:
        _draw_no_data(image, draw, header_bottom, logo_path, fallback_text)
        return image

    _draw_table_header(draw, view.columns, CONTENT_TOP + 7)

    for index, station in enumerate(rows):
        y = rows_top + index * ROW_HEIGHT
        draw.rectangle((0, y, 63, y + ROW_HEIGHT - 1), fill=ROW_BG[index % len(ROW_BG)])
        _draw_row(draw, view, station, y, index)

    # Logo + clock last, so the logo sits on top of the header band's left side.
    draw_top_bar(image, draw, logo_path, fallback_text)
    return image


def _draw_no_data(
    image: Image.Image,
    draw: ImageDraw.ImageDraw,
    header_bottom: int,
    logo_path: Path | None,
    fallback_text: str,
) -> None:
    from .fonts import FONT_5X7_HEIGHT

    no_data = "NO DATA"
    x = max(0, (64 - small_text_width(no_data)) // 2)
    y = header_bottom + max(0, (64 - header_bottom - FONT_5X7_HEIGHT) // 2)
    draw_small_text(draw, x, y, no_data, (255, 80, 80))
    draw_top_bar(image, draw, logo_path, fallback_text)


def _draw_table_header(draw: ImageDraw.ImageDraw, columns: list[Column], y: int) -> None:
    for column in columns:
        if column.icon == "bike":
            draw_bike_icon(draw, column.center_x - 6, y, column.color)
        elif column.icon == "bolt":
            draw_bolt_icon(draw, column.center_x - 2, y + 1, column.color)
        else:
            draw_tiny_text(draw, column.center_x - 2, y + 1, column.icon, column.color)


def _draw_row(
    draw: ImageDraw.ImageDraw,
    view: BikeShareView,
    station: StationRow,
    y: int,
    row_index: int,
) -> None:
    name = clip_text(station.name, view.name_max_width)
    text_y = y + max(0, (ROW_HEIGHT - FONT_4X6_HEIGHT) // 2)
    draw_station_name(draw, 0, text_y, name, NAME_TINTS[row_index % len(NAME_TINTS)])

    for column, value in zip(view.columns, station.values):
        text = _clipped_metric(value)
        width = tiny_text_width(text)
        if len(text) == 1:
            number_x = column.center_x - width // 2  # single digit: centre under the icon
        else:
            number_x = column.right - width          # multi-digit: right-aligned to the edge
        draw_tiny_text(draw, number_x, text_y, text, column.color)


def _clipped_metric(value: int) -> str:
    return "99" if value > 99 else str(max(0, value))
