"""Menus for the 1.3" 240x240 IPS LCD (ST7789).

Pure and hardware-free: models a selectable list and renders it to a Pillow
image. The hardware glue (SPI driver + buttons) lives in ``controller.py``.

Two screens are used, in order:

1. Language : Français / English  -> config ``"language"`` ("fr" / "en")
2. Display mode (localized)        -> config ``"mode"``
       1. Vélo uniquement              -> "velo"
       2. Vélo + Communauto (10 s)     -> "velo_communauto"
       3. Communauto uniquement        -> "communauto"
"""

from __future__ import annotations

from dataclasses import dataclass

from PIL import Image, ImageDraw, ImageFont

SCREEN_SIZE = 240

MODE_KEYS = ("velo", "velo_communauto", "communauto")
LANGUAGES = ("fr", "en")

# Localized strings for the mode menu.
MODE_STRINGS = {
    "fr": {
        "title": "Mode d'affichage",
        "footer": "Joystick: choisir · valider",
        "confirmed": "Validé ✓",
        "options": [
            ("velo", "Vélo", "àVélo seul"),
            ("velo_communauto", "Vélo + Communauto", "alternance 10 s"),
            ("communauto", "Communauto", "autos seul"),
        ],
    },
    "en": {
        "title": "Display mode",
        "footer": "Joystick: choose · select",
        "confirmed": "Saved ✓",
        "options": [
            ("velo", "Bike", "àVélo only"),
            ("velo_communauto", "Bike + Communauto", "switch 10 s"),
            ("communauto", "Communauto", "cars only"),
        ],
    },
}

# Localized strings for the main menu and the brightness screen.
MAIN_STRINGS = {
    "fr": {
        "title": "Réglages",
        "footer": "Joystick: choisir · ouvrir",
        "options": [
            ("mode", "Mode d'affichage", ""),
            ("brightness", "Luminosité", ""),
            ("sleep", "Veille du soir", ""),
            ("language", "Langue", ""),
        ],
    },
    "en": {
        "title": "Settings",
        "footer": "Joystick: choose · open",
        "options": [
            ("mode", "Display mode", ""),
            ("brightness", "Brightness", ""),
            ("sleep", "Evening off", ""),
            ("language", "Language", ""),
        ],
    },
}

SLEEP_STRINGS = {
    "fr": {
        "title": "Veille du soir",
        "footer": "↕ champ · ←/→ régler · OK",
        "confirmed": "Validé ✓",
        "enabled": "État", "on": "Activée", "off": "Désactivée",
        "off_at": "Éteindre à", "on_at": "Rallumer à",
    },
    "en": {
        "title": "Evening off",
        "footer": "↕ field · ←/→ adjust · OK",
        "confirmed": "Saved ✓",
        "enabled": "State", "on": "On", "off": "Off",
        "off_at": "Off at", "on_at": "On at",
    },
}

TIME_STEP_MIN = 30

BRIGHTNESS_STRINGS = {
    "fr": {"title": "Luminosité", "footer": "Joystick ←/→ · valider", "confirmed": "Validé ✓"},
    "en": {"title": "Brightness", "footer": "Joystick ←/→ · select", "confirmed": "Saved ✓"},
}

BRIGHTNESS_STEP = 5

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


def _fit_font(draw: ImageDraw.ImageDraw, texts: list[str], max_width: int, largest: int, smallest: int):
    """Largest font size (largest..smallest) at which every text fits ``max_width``."""
    for size in range(largest, smallest - 1, -1):
        font = _load_font(size)
        if all(draw.textlength(text, font=font) <= max_width for text in texts):
            return font
    return _load_font(smallest)


@dataclass
class ListMenu:
    """A vertical list of selectable options rendered to a 240x240 image."""

    title: str
    options: list[tuple[str, str, str]]  # (key, label, sublabel)
    footer: str = ""
    confirmed_footer: str = "✓"
    selected: int = 0
    active_key: str | None = None

    def __post_init__(self) -> None:
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

        draw.text((16, 12), self.title, font=title_font, fill=TITLE)
        draw.line((16, 44, SCREEN_SIZE - 16, 44), fill=(60, 64, 72))

        label_x = 46
        dot_margin = 26  # space reserved at the right for the active marker
        avail = (SCREEN_SIZE - 12) - label_x - dot_margin
        label_font = _fit_font(draw, [label for _, label, _ in self.options], avail, 22, 14)

        count = len(self.options)
        gap = 8
        # Fit the rows in the area below the title; taller rows when fewer options.
        area_top, area_bottom = 52, SCREEN_SIZE - 28
        row_height = min(64, (area_bottom - area_top - gap * (count - 1)) // count)
        for index, (key, label, sublabel) in enumerate(self.options):
            y = area_top + index * (row_height + gap)
            is_selected = index == self.selected
            draw.rounded_rectangle(
                (12, y, SCREEN_SIZE - 12, y + row_height),
                radius=10,
                fill=ROW_BG_SELECTED if is_selected else ROW_BG,
            )
            label_y = y + (8 if sublabel else (row_height - 22) // 2)
            draw.text((22, label_y), str(index + 1), font=label_font,
                      fill=TITLE if is_selected else TEXT_DIM)
            draw.text((label_x, label_y), label, font=label_font,
                      fill=TITLE if is_selected else TEXT)
            if sublabel:
                draw.text((label_x, y + row_height - 20), sublabel, font=sub_font,
                          fill=(220, 240, 225) if is_selected else TEXT_DIM)
            if key == self.active_key:
                cy = y + row_height // 2
                draw.ellipse((SCREEN_SIZE - 30, cy - 6, SCREEN_SIZE - 18, cy + 6), fill=ACCENT)

        footer = self.confirmed_footer if confirmed else self.footer
        if footer:
            draw.text((16, SCREEN_SIZE - 22), footer, font=sub_font,
                      fill=ACCENT if confirmed else TEXT_DIM)
        return image


def language_menu(active_key: str | None = None) -> ListMenu:
    return ListMenu(
        title="Langue / Language",
        options=[("fr", "Français", ""), ("en", "English", "")],
        footer="Joystick · valider / select",
        confirmed_footer="✓",
        active_key=active_key,
    )


def mode_menu(lang: str = "fr", active_key: str | None = None) -> ListMenu:
    strings = MODE_STRINGS.get(lang, MODE_STRINGS["fr"])
    return ListMenu(
        title=strings["title"],
        options=list(strings["options"]),
        footer=strings["footer"],
        confirmed_footer=strings["confirmed"],
        active_key=active_key,
    )


def main_menu(lang: str = "fr", selected: int = 0) -> ListMenu:
    strings = MAIN_STRINGS.get(lang, MAIN_STRINGS["fr"])
    return ListMenu(
        title=strings["title"],
        options=list(strings["options"]),
        footer=strings["footer"],
        selected=selected,
    )


@dataclass
class BrightnessScreen:
    """A 0-100 brightness adjuster (joystick left/right) with a level bar."""

    value: int
    lang: str = "fr"
    step: int = BRIGHTNESS_STEP

    def __post_init__(self) -> None:
        self.value = _clamp(self.value)

    def adjust(self, delta: int) -> None:
        self.value = _clamp(self.value + delta * self.step)

    def render(self, confirmed: bool = False) -> Image.Image:
        strings = BRIGHTNESS_STRINGS.get(self.lang, BRIGHTNESS_STRINGS["fr"])
        image = Image.new("RGB", (SCREEN_SIZE, SCREEN_SIZE), BG)
        draw = ImageDraw.Draw(image)

        draw.text((16, 12), strings["title"], font=_load_font(24), fill=TITLE)
        draw.line((16, 44, SCREEN_SIZE - 16, 44), fill=(60, 64, 72))

        # Big percentage, centred.
        big = _load_font(64)
        text = f"{self.value}%"
        width = draw.textlength(text, font=big)
        draw.text(((SCREEN_SIZE - width) // 2, 70), text, font=big, fill=TITLE)

        # Level bar.
        x0, x1, y0, y1 = 24, SCREEN_SIZE - 24, 162, 184
        draw.rounded_rectangle((x0, y0, x1, y1), radius=8, fill=ROW_BG)
        fill_w = int((x1 - x0 - 4) * self.value / 100)
        if fill_w > 0:
            draw.rounded_rectangle((x0 + 2, y0 + 2, x0 + 2 + fill_w, y1 - 2), radius=6, fill=ACCENT)

        footer = strings["confirmed"] if confirmed else strings["footer"]
        draw.text((16, SCREEN_SIZE - 22), footer, font=_load_font(13),
                  fill=ACCENT if confirmed else TEXT_DIM)
        return image


def _clamp(value: int) -> int:
    return max(0, min(100, int(value)))


def minutes_to_hhmm(minutes: int) -> str:
    minutes %= 24 * 60
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def hhmm_to_minutes(value: str, default: int) -> int:
    try:
        hours, mins = str(value).strip().split(":")
        total = int(hours) * 60 + int(mins)
    except (ValueError, AttributeError):
        return default
    return total % (24 * 60)


@dataclass
class SleepScreen:
    """Evening-off editor: enable toggle + off time + on time (joystick)."""

    enabled: bool
    off_minutes: int
    on_minutes: int
    lang: str = "fr"
    field: int = 0  # 0 = state, 1 = off time, 2 = on time

    def move(self, delta: int) -> None:
        self.field = (self.field + delta) % 3

    def adjust(self, delta: int) -> None:
        if self.field == 0:
            self.enabled = not self.enabled
        elif self.field == 1:
            self.off_minutes = (self.off_minutes + delta * TIME_STEP_MIN) % (24 * 60)
        else:
            self.on_minutes = (self.on_minutes + delta * TIME_STEP_MIN) % (24 * 60)

    def render(self, confirmed: bool = False) -> Image.Image:
        strings = SLEEP_STRINGS.get(self.lang, SLEEP_STRINGS["fr"])
        image = Image.new("RGB", (SCREEN_SIZE, SCREEN_SIZE), BG)
        draw = ImageDraw.Draw(image)

        draw.text((16, 12), strings["title"], font=_load_font(24), fill=TITLE)
        draw.line((16, 44, SCREEN_SIZE - 16, 44), fill=(60, 64, 72))

        label_font = _load_font(18)
        value_font = _load_font(18)
        rows = [
            (strings["enabled"], strings["on"] if self.enabled else strings["off"]),
            (strings["off_at"], minutes_to_hhmm(self.off_minutes)),
            (strings["on_at"], minutes_to_hhmm(self.on_minutes)),
        ]
        row_height = 50
        top = 56
        for index, (label, value) in enumerate(rows):
            y = top + index * (row_height + 6)
            is_selected = index == self.field
            # Disabled times are dimmed.
            dim = (not self.enabled) and index > 0
            draw.rounded_rectangle(
                (12, y, SCREEN_SIZE - 12, y + row_height),
                radius=10,
                fill=ROW_BG_SELECTED if is_selected else ROW_BG,
            )
            draw.text((24, y + 15), label, font=label_font,
                      fill=TITLE if is_selected else (TEXT_DIM if dim else TEXT))
            vw = draw.textlength(value, font=value_font)
            draw.text((SCREEN_SIZE - 28 - vw, y + 15), value, font=value_font,
                      fill=TITLE if is_selected else (TEXT_DIM if dim else ACCENT))

        footer = strings["confirmed"] if confirmed else strings["footer"]
        draw.text((16, SCREEN_SIZE - 22), footer, font=_load_font(13),
                  fill=ACCENT if confirmed else TEXT_DIM)
        return image


def sleep_screen(lang: str, enabled: bool, off_start: str, off_end: str) -> SleepScreen:
    return SleepScreen(
        enabled=enabled,
        off_minutes=hhmm_to_minutes(off_start, 21 * 60),
        on_minutes=hhmm_to_minutes(off_end, 8 * 60),
        lang=lang,
    )
