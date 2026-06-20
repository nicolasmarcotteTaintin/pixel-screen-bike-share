"""Small hand-drawn glyph icons used in headers and rows."""

from __future__ import annotations

from PIL import ImageDraw


def draw_bike_icon(draw: ImageDraw.ImageDraw, x: int, y: int, color: tuple[int, int, int]) -> None:
    # 13x7 step-through city bike: low open frame, upright seat and handlebar.
    draw.ellipse((x + 0, y + 2, x + 4, y + 6), outline=color)   # rear wheel
    draw.ellipse((x + 8, y + 2, x + 12, y + 6), outline=color)  # front wheel
    draw.point((x + 2, y + 4), fill=color)                      # rear hub
    draw.point((x + 10, y + 4), fill=color)                     # front hub
    draw.line((x + 2, y + 4, x + 2, y + 1), fill=color)         # seat tube (upright)
    draw.point((x + 1, y + 0), fill=color)                      # seat
    draw.point((x + 2, y + 0), fill=color)
    draw.line((x + 10, y + 4, x + 9, y + 1), fill=color)        # head tube (upright)
    draw.point((x + 8, y + 0), fill=color)                      # swept-back handlebar
    draw.point((x + 9, y + 0), fill=color)
    draw.point((x + 10, y + 0), fill=color)
    draw.line((x + 2, y + 3, x + 5, y + 4), fill=color)         # step-through frame: dip down
    draw.line((x + 5, y + 4, x + 8, y + 4), fill=color)         # low bar to step over
    draw.line((x + 8, y + 4, x + 9, y + 2), fill=color)         # rise to head tube


def draw_bolt_icon(draw: ImageDraw.ImageDraw, x: int, y: int, color: tuple[int, int, int]) -> None:
    # 5x6 lightning bolt, occupying rows y..y+5.
    points = [(x + 3, y), (x, y + 3), (x + 2, y + 3), (x + 1, y + 5), (x + 4, y + 2), (x + 2, y + 2)]
    draw.polygon(points, fill=color)


def draw_car_icon(draw: ImageDraw.ImageDraw, x: int, y: int, color: tuple[int, int, int]) -> None:
    # 11x6 compact side-view car: cabin, hood, two wheels.
    draw.line((x + 2, y + 1, x + 6, y + 1), fill=color)         # roof
    draw.line((x + 1, y + 2, x + 2, y + 1), fill=color)         # windshield
    draw.line((x + 6, y + 1, x + 8, y + 2), fill=color)         # rear glass
    draw.line((x + 0, y + 3, x + 10, y + 3), fill=color)        # body/beltline
    draw.line((x + 0, y + 3, x + 0, y + 4), fill=color)         # front bumper
    draw.line((x + 10, y + 3, x + 10, y + 4), fill=color)       # rear bumper
    draw.line((x + 1, y + 4, x + 9, y + 4), fill=color)         # sill
    draw.ellipse((x + 1, y + 4, x + 3, y + 6), outline=color)   # front wheel
    draw.ellipse((x + 7, y + 4, x + 9, y + 6), outline=color)   # rear wheel


# 3x5 compass arrows keyed by 8-point cardinal direction. Drawn pixel by pixel.
_ARROWS = {
    "N":  ("010", "111", "010", "010", "010"),
    "S":  ("010", "010", "010", "111", "010"),
    "E":  ("000", "001", "111", "001", "000"),
    "W":  ("000", "100", "111", "100", "000"),
    "NE": ("0011", "0001", "0101", "1000", "0000"),
    "NW": ("1100", "1000", "1010", "0001", "0000"),
    "SE": ("0000", "1000", "0101", "0001", "0011"),
    "SW": ("0000", "0001", "1010", "1000", "1100"),
}


def draw_arrow(draw: ImageDraw.ImageDraw, x: int, y: int, direction: str, color: tuple[int, int, int]) -> int:
    """Draw a small compass arrow for ``direction`` (N/NE/.../NW). Returns its width in px."""
    glyph = _ARROWS.get(direction.upper())
    if glyph is None:
        return 0
    for row_index, row in enumerate(glyph):
        for col_index, pixel in enumerate(row):
            if pixel == "1":
                draw.point((x + col_index, y + row_index), fill=color)
    return len(glyph[0])
