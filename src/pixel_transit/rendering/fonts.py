"""Hand-drawn pixel fonts and text helpers for the 64x64 Pixoo canvas.

Three fonts are used across the display:

* ``FONT_5X7`` — the main 5x7 font (clock, large labels).
* ``FONT_4X6`` — a compact 4x6 font (station names, metric counters).
* ``PIXEL_GLYPHS`` — a tiny 3x5 font scaled up for the text logo fallback.
"""

from __future__ import annotations

from PIL import ImageDraw


# --- 5x7 main font -----------------------------------------------------------

FONT_5X7 = {
    " ": ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    "-": ("00000", "00000", "00000", "11111", "00000", "00000", "00000"),
    ".": ("00000", "00000", "00000", "00000", "00000", "00000", "00100"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00010", "00100", "01000", "11111"),
    "3": ("11111", "00010", "00100", "00010", "00001", "10001", "01110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    "6": ("00110", "01000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00010", "01100"),
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01110", "10001", "10000", "10111", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    "J": ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "11001", "10101", "10011", "10011", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "10101", "01010"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
}

FONT_5X7_WIDTH = 5
FONT_5X7_HEIGHT = 7


def draw_small_text(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    text: str,
    color: tuple[int, int, int],
) -> None:
    cursor = x
    for character in text:
        glyph = FONT_5X7.get(character.upper())
        if glyph is None:
            cursor += FONT_5X7_WIDTH + 1
            continue
        for row_index, row in enumerate(glyph):
            for col_index, pixel in enumerate(row):
                if pixel == "1":
                    draw.point((cursor + col_index, y + row_index), fill=color)
        cursor += FONT_5X7_WIDTH + 1


def small_text_width(text: str) -> int:
    if not text:
        return 0
    return len(text) * (FONT_5X7_WIDTH + 1) - 1


# --- 4x6 compact font --------------------------------------------------------

FONT_4X6 = {
    "0": ("0110", "1001", "1001", "1001", "1001", "0110"),
    "1": ("0010", "0110", "0010", "0010", "0010", "0111"),
    "2": ("0110", "1001", "0001", "0010", "0100", "1111"),
    "3": ("1110", "0001", "0110", "0001", "1001", "0110"),
    "4": ("0010", "0110", "1010", "1111", "0010", "0010"),
    "5": ("1111", "1000", "1110", "0001", "1001", "0110"),
    "6": ("0110", "1000", "1110", "1001", "1001", "0110"),
    "7": ("1111", "0001", "0010", "0010", "0100", "0100"),
    "8": ("0110", "1001", "0110", "1001", "1001", "0110"),
    "9": ("0110", "1001", "1001", "0111", "0001", "0110"),
    " ": ("0000", "0000", "0000", "0000", "0000", "0000"),
    "-": ("0000", "0000", "0000", "1111", "0000", "0000"),
    ".": ("0000", "0000", "0000", "0000", "0000", "0100"),
    "A": ("0110", "1001", "1001", "1111", "1001", "1001"),
    "B": ("1110", "1001", "1110", "1001", "1001", "1110"),
    "C": ("0111", "1000", "1000", "1000", "1000", "0111"),
    "D": ("1110", "1001", "1001", "1001", "1001", "1110"),
    "E": ("1111", "1000", "1110", "1000", "1000", "1111"),
    "F": ("1111", "1000", "1110", "1000", "1000", "1000"),
    "G": ("0111", "1000", "1000", "1011", "1001", "0111"),
    "H": ("1001", "1001", "1111", "1001", "1001", "1001"),
    "I": ("1110", "0100", "0100", "0100", "0100", "1110"),
    "J": ("0111", "0010", "0010", "0010", "1010", "0100"),
    "K": ("1001", "1010", "1100", "1100", "1010", "1001"),
    "L": ("1000", "1000", "1000", "1000", "1000", "1111"),
    "M": ("1001", "1111", "1111", "1001", "1001", "1001"),
    "N": ("1001", "1101", "1101", "1011", "1011", "1001"),
    "O": ("0110", "1001", "1001", "1001", "1001", "0110"),
    "P": ("1110", "1001", "1001", "1110", "1000", "1000"),
    "Q": ("0110", "1001", "1001", "1001", "1011", "0111"),
    "R": ("1110", "1001", "1001", "1110", "1010", "1001"),
    "S": ("0111", "1000", "0110", "0001", "0001", "1110"),
    "T": ("1111", "0100", "0100", "0100", "0100", "0100"),
    "U": ("1001", "1001", "1001", "1001", "1001", "0110"),
    "V": ("1001", "1001", "1001", "1001", "0110", "0110"),
    "W": ("1001", "1001", "1001", "1111", "1111", "1001"),
    "X": ("1001", "1001", "0110", "0110", "1001", "1001"),
    "Y": ("1001", "1001", "0110", "0100", "0100", "0100"),
    "Z": ("1111", "0001", "0010", "0100", "1000", "1111"),
}

FONT_4X6_WIDTH = 4
FONT_4X6_HEIGHT = 6


def draw_tiny_text(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    text: str,
    color: tuple[int, int, int],
) -> None:
    cursor = x
    for character in text:
        glyph = FONT_4X6.get(character.upper())
        if glyph is None:
            cursor += FONT_4X6_WIDTH + 1
            continue
        for row_index, row in enumerate(glyph):
            for col_index, pixel in enumerate(row):
                if pixel == "1":
                    draw.point((cursor + col_index, y + row_index), fill=color)
        cursor += FONT_4X6_WIDTH + 1


def tiny_text_width(text: str) -> int:
    if not text:
        return 0
    return len(text) * (FONT_4X6_WIDTH + 1) - 1


# --- Station names with French ordinal superscripts (e.g. 2e, 1er, 1re) ------

# 3x4 superscript glyphs for ordinal letters following a digit.
SUPERSCRIPT = {
    "E": ("111", "100", "110", "111"),
    "R": ("110", "101", "110", "101"),
    "D": ("110", "101", "101", "110"),
    "S": ("011", "110", "001", "110"),
    "N": ("101", "111", "111", "101"),
    "T": ("111", "010", "010", "010"),
}
SUPERSCRIPT_WIDTH = 3


def draw_station_name(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    text: str,
    color: tuple[int, int, int],
) -> None:
    """Draw a 4x6 name, rendering ordinal letters that follow a digit as small superscripts."""
    cursor = x
    ordinal = False  # True right after a digit: following letters are the ordinal suffix
    for character in text:
        upper = character.upper()
        if ordinal and not character.isdigit() and upper in SUPERSCRIPT:
            glyph = SUPERSCRIPT[upper]
            for row_index, row in enumerate(glyph):
                for col_index, pixel in enumerate(row):
                    if pixel == "1":
                        draw.point((cursor + col_index, y + row_index), fill=color)
            cursor += SUPERSCRIPT_WIDTH + 1
            continue

        ordinal = character.isdigit()
        glyph = FONT_4X6.get(upper)
        if glyph is not None:
            for row_index, row in enumerate(glyph):
                for col_index, pixel in enumerate(row):
                    if pixel == "1":
                        draw.point((cursor + col_index, y + row_index), fill=color)
        cursor += FONT_4X6_WIDTH + 1


def station_name_width(text: str) -> int:
    """Rendered width of a name, accounting for narrower ordinal superscripts."""
    width = 0
    ordinal = False
    for character in text:
        if ordinal and not character.isdigit() and character.upper() in SUPERSCRIPT:
            width += SUPERSCRIPT_WIDTH + 1
            continue
        ordinal = character.isdigit()
        width += FONT_4X6_WIDTH + 1
    return max(0, width - 1)


def clip_text(text: str, max_width: int) -> str:
    """Trim from the right until the rendered 4x6 width fits ``max_width``."""
    while text and station_name_width(text) > max_width:
        text = text[:-1]
    return text


# --- 3x5 logo fallback font --------------------------------------------------

PIXEL_GLYPHS = {
    "0": ("111", "101", "101", "101", "111"),
    "1": ("010", "110", "010", "010", "111"),
    "2": ("111", "001", "111", "100", "111"),
    "3": ("111", "001", "111", "001", "111"),
    "4": ("101", "101", "111", "001", "001"),
    "5": ("111", "100", "111", "001", "111"),
    "6": ("111", "100", "111", "101", "111"),
    "7": ("111", "001", "010", "010", "010"),
    "8": ("111", "101", "111", "101", "111"),
    "9": ("111", "101", "111", "001", "111"),
    "A": ("111", "101", "111", "101", "101"),
    "B": ("110", "101", "110", "101", "110"),
    "C": ("011", "100", "100", "100", "011"),
    "E": ("111", "100", "110", "100", "111"),
    "I": ("111", "010", "010", "010", "111"),
    "L": ("100", "100", "100", "100", "111"),
    "O": ("111", "101", "101", "101", "111"),
    "P": ("110", "101", "110", "100", "100"),
    "V": ("101", "101", "101", "101", "010"),
    "X": ("101", "101", "010", "101", "101"),
}


def draw_pixel_text(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    text: str,
    color: tuple[int, int, int],
    scale: int = 2,
) -> None:
    cursor = x
    for character in text:
        glyph = PIXEL_GLYPHS.get(character.upper())
        if not glyph:
            cursor += 2 * scale
            continue
        for row_index, row in enumerate(glyph):
            for col_index, pixel in enumerate(row):
                if pixel == "1":
                    x0 = cursor + col_index * scale
                    y0 = y + row_index * scale
                    draw.rectangle((x0, y0, x0 + scale - 1, y0 + scale - 1), fill=color)
        cursor += (len(glyph[0]) + 1) * scale


def pixel_text_width(text: str, scale: int = 2) -> int:
    width = 0
    for character in text:
        glyph = PIXEL_GLYPHS.get(character.upper())
        width += ((len(glyph[0]) + 1) if glyph else 2) * scale
    return max(0, width - scale)
