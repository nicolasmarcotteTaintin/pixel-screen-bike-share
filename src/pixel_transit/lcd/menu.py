"""Mode-selection menu for the 1.3" 240x240 IPS LCD (ST7789).

This module is pure and hardware-free: it models the menu state and renders it
to a Pillow image. The hardware glue (SPI driver + buttons) lives in
``controller.py`` so this part can be unit-tested and previewed anywhere.

The menu lets the user pick one of the three display modes:

    1. Vélo uniquement              -> "velo"
    2. Vélo + Communauto (10 s)     -> "velo_communauto"
    3. Communauto uniquement        -> "communauto"
"""

from __future__ import annotations

from dataclasses import dataclass

from PIL import Image, ImageDraw, ImageFont

SCREEN_SIZE = 240

# Display modes shown in the menu, in order, with the config value they map to.
MENU_OPTIONS: list[tuple[str, str, str]] = [
    ("velo", "Vélo", "àVélo seul"),
    ("velo_communauto", "Vélo + Communauto", "alternance 10 s"),
    ("communauto", "Communauto", "autos seul"),
]

# Palette (RGB).
BG = (16, 18, 22)
TITLE = (245, 245, 245)
ROW_BG = (30, 33, 40)
ROW_BG_SELECTED = (0, 120, 60)
TEXT = (230, 230, 230)
TEXT_DIM = (150, 155, 165)
ACCENT = (76, 235, 115)

_FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/Library/Fonts/Arial.ttf",
]


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in _FONT_CANDIDATES:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _text_width(draw: ImageDraw.ImageDraw, text: str, font) -> float:
    return draw.textlength(text, font=font)


def _fit_font(draw: ImageDraw.ImageDraw, texts: list[str], max_width: int, largest: int, smallest: int):
    """Largest font size (largest..smallest) at which every text fits ``max_width``."""
    for size in range(largest, smallest - 1, -1):
        font = _load_font(size)
        if all(_text_width(draw, text, font) <= max_width for text in texts):
            return font
    return _load_font(smallest)


@dataclass
class Menu:
    """Selectable list of display modes.

    ``selected`` is the highlighted row; ``active_key`` is the mode currently
    saved in the config (marked with a dot).
    """

    selected: int = 0
    active_key: str | None = None
    options: list[tuple[str, str, str]] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.options is None:
            self.options = MENU_OPTIONS
        if self.active_key is not None:
            for index, (key, _, _) in enumerate(self.options):
                if key == self.active_key:
                    self.selected = index
                    break

    def move(self, delta: int) -> None:
        self.selected = (self.selected + delta) % len(self.options)

    def select_index(self, index: int) -> None:
        if 0 <= index < len(self.options):
            self.selected = index

    @property
    def current_key(self) -> str:
        return self.options[self.selected][0]

    def render(self, confirmed: bool = False) -> Image.Image:
        image = Image.new("RGB", (SCREEN_SIZE, SCREEN_SIZE), BG)
        draw = ImageDraw.Draw(image)

        title_font = _load_font(24)
        sub_font = _load_font(13)

        draw.text((16, 12), "Mode d'affichage", font=title_font, fill=TITLE)
        draw.line((16, 44, SCREEN_SIZE - 16, 44), fill=(60, 64, 72))

        label_x = 46
        dot_margin = 26  # space reserved at the right for the active-mode dot
        avail = (SCREEN_SIZE - 12) - label_x - dot_margin
        label_font = _fit_font(draw, [label for _, label, _ in self.options], avail, 22, 14)

        row_height = 52
        top = 52
        gap = 8
        for index, (key, label, sublabel) in enumerate(self.options):
            y = top + index * (row_height + gap)
            is_selected = index == self.selected
            draw.rounded_rectangle(
                (12, y, SCREEN_SIZE - 12, y + row_height),
                radius=10,
                fill=ROW_BG_SELECTED if is_selected else ROW_BG,
            )
            draw.text((22, y + 8), str(index + 1), font=label_font,
                      fill=TITLE if is_selected else TEXT_DIM)
            draw.text((label_x, y + 6), label, font=label_font,
                      fill=TITLE if is_selected else TEXT)
            draw.text((label_x, y + 32), sublabel, font=sub_font,
                      fill=(220, 240, 225) if is_selected else TEXT_DIM)
            if key == self.active_key:
                cy = y + row_height // 2
                draw.ellipse((SCREEN_SIZE - 30, cy - 6, SCREEN_SIZE - 18, cy + 6), fill=ACCENT)

        footer = "Validé ✓" if confirmed else "Joystick: choisir · valider"
        draw.text((16, SCREEN_SIZE - 22), footer, font=sub_font,
                  fill=ACCENT if confirmed else TEXT_DIM)
        return image
