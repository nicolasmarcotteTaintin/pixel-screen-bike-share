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
        "title": "Mode affichage",
        "footer": "Joystick: choisir · valider",
        "confirmed": "Validé ✓",
        "options": [
            ("velo", "Vélo", ""),
            ("velo_communauto", "Vélo + Comm.", ""),
            ("communauto", "Communauto", ""),
        ],
    },
    "en": {
        "title": "Display mode",
        "footer": "Joystick: choose · select",
        "confirmed": "Saved ✓",
        "options": [
            ("velo", "Bike", ""),
            ("velo_communauto", "Bike + Comm.", ""),
            ("communauto", "Communauto", ""),
        ],
    },
}

# Localized strings for the main menu and the brightness screen.
MAIN_STRINGS = {
    "fr": {
        "title": "Réglages",
        "footer": "Joystick: choisir · ouvrir",
        "options": [
            ("mode", "Mode affichage", ""),
            ("rotate", "Alternance", ""),
            ("brightness", "Luminosité écran", ""),
            ("lcd_brightness", "Luminosité Pi", ""),
            ("sleep", "Veille du soir", ""),
            ("language", "Langue", ""),
            ("info", "Information", ""),
            ("exit", "Éteindre l'écran", ""),
        ],
    },
    "en": {
        "title": "Settings",
        "footer": "Joystick: choose · open",
        "options": [
            ("mode", "Display mode", ""),
            ("rotate", "Alternation", ""),
            ("brightness", "Screen brightness", ""),
            ("lcd_brightness", "Pi brightness", ""),
            ("sleep", "Evening off", ""),
            ("language", "Language", ""),
            ("info", "Information", ""),
            ("exit", "Turn off screen", ""),
        ],
    },
}

# Rotation (alternate mode) interval choices, in seconds.
ROTATE_OPTIONS = (5, 10, 15, 20, 30, 60)

ROTATE_STRINGS = {
    "fr": {
        "title": "Alternance",
        "footer": "Joystick ←/→ · valider",
        "confirmed": "Validé ✓",
        "unit": "s",
        "disabled_hint": "Mode Vélo + Communauto requis",
    },
    "en": {
        "title": "Alternation",
        "footer": "Joystick ←/→ · select",
        "confirmed": "Saved ✓",
        "unit": "s",
        "disabled_hint": "Needs Bike + Communauto mode",
    },
}

# Information screen: ordered (value-key, localized label) rows.
INFO_STRINGS = {
    "fr": {
        "title": "Information",
        "footer": "Un bouton: retour",
        "rows": [
            ("host", "Appareil"),
            ("ip", "Adresse IP"),
            ("ssid", "Wi-Fi"),
            ("mode", "Mode"),
            ("network", "Réseau vélo"),
            ("pixoo", "Pixoo"),
            ("brightness", "Luminosité"),
        ],
    },
    "en": {
        "title": "Information",
        "footer": "Any button: back",
        "rows": [
            ("host", "Device"),
            ("ip", "IP address"),
            ("ssid", "Wi-Fi"),
            ("mode", "Mode"),
            ("network", "Bike network"),
            ("pixoo", "Pixoo"),
            ("brightness", "Brightness"),
        ],
    },
}

SLEEP_STRINGS = {
    "fr": {
        "title": "Veille du soir",
        "footer": "↕ champ · ←/→ régler · OK",
        "confirmed": "Validé ✓",
        "enabled": "État", "on": "Activée", "off": "Désactivée",
        "trigger": "Déclencheur", "sunset": "Soleil", "fixed": "Heure fixe",
        "off_at": "Éteindre à", "on_at": "Rallumer à",
    },
    "en": {
        "title": "Evening off",
        "footer": "↕ field · ←/→ adjust · OK",
        "confirmed": "Saved ✓",
        "enabled": "State", "on": "On", "off": "Off",
        "trigger": "Trigger", "sunset": "Sunset", "fixed": "Fixed time",
        "off_at": "Off at", "on_at": "On at",
    },
}

TIME_STEP_MIN = 30

BRIGHTNESS_STRINGS = {
    "fr": {"title": "Luminosité", "footer": "Joystick ←/→ · valider", "confirmed": "Validé ✓"},
    "en": {"title": "Brightness", "footer": "Joystick ←/→ · select", "confirmed": "Saved ✓"},
}

# Titles for the two brightness targets: the Pixoo LED panel vs the Pi's LCD HAT.
BRIGHTNESS_TITLES = {
    "screen": {"fr": "Luminosité écran", "en": "Screen brightness"},
    "pi": {"fr": "Luminosité Pi", "en": "Pi brightness"},
}

BRIGHTNESS_STEP = 5

# Palette (RGB). Pure-black background for maximum contrast on the IPS panel.
BG = (0, 0, 0)
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
    disabled_keys: frozenset = frozenset()  # keys rendered greyed-out (still selectable)
    max_visible: int = 5  # rows shown at once; longer lists scroll (scrollbar on the right)

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

    def is_disabled(self, key: str) -> bool:
        return key in self.disabled_keys

    def _window(self) -> tuple[int, int]:
        """(start, count) of the visible slice, kept centred on the selection."""
        count = len(self.options)
        visible = min(count, self.max_visible)
        if count <= visible:
            return 0, visible
        start = min(max(0, self.selected - visible // 2), count - visible)
        return start, visible

    def render(self, confirmed: bool = False) -> Image.Image:
        image = Image.new("RGB", (SCREEN_SIZE, SCREEN_SIZE), BG)
        draw = ImageDraw.Draw(image)

        sub_font = _load_font(12)
        draw.text((16, 12), self.title, font=_load_font(24), fill=TITLE)
        draw.line((16, 44, SCREEN_SIZE - 16, 44), fill=(60, 64, 72))

        start, visible = self._window()
        count = len(self.options)
        gap = 8 if visible <= 5 else 6
        area_top, area_bottom = 50, SCREEN_SIZE - 26
        row_height = min(60, (area_bottom - area_top - gap * (visible - 1)) // visible)

        label_x = 46
        # Reserve text room on the right only for the active-marker dot; the
        # scrollbar sits in the outer margin, so marker-less menus get more width.
        text_margin = 26 if self.active_key else 14
        avail = (SCREEN_SIZE - 12) - label_x - text_margin
        max_label = 24 if visible <= 5 else max(13, min(20, row_height - 4))
        label_font = _fit_font(draw, [label for _, label, _ in self.options], avail, max_label, 12)
        label_h = draw.textbbox((0, 0), "Ag", font=label_font)[3]

        for slot in range(visible):
            index = start + slot
            key, label, sublabel = self.options[index]
            y = area_top + slot * (row_height + gap)
            disabled = self.is_disabled(key)
            is_selected = index == self.selected
            has_sub = bool(sublabel) and row_height >= 40

            if disabled:
                fill = (40, 43, 50) if is_selected else ROW_BG
                num_color, text_color = (82, 88, 98), (120, 126, 138)
            elif is_selected:
                fill, num_color, text_color = ROW_BG_SELECTED, TITLE, TITLE
            else:
                fill, num_color, text_color = ROW_BG, TEXT_DIM, TEXT

            draw.rounded_rectangle((12, y, SCREEN_SIZE - 12, y + row_height), radius=10, fill=fill)
            label_y = y + 8 if has_sub else y + max(2, (row_height - label_h) // 2)
            draw.text((22, label_y), str(index + 1), font=label_font, fill=num_color)
            draw.text((label_x, label_y), label, font=label_font, fill=text_color)
            if has_sub:
                draw.text((label_x, y + row_height - 20), sublabel, font=sub_font,
                          fill=(220, 240, 225) if is_selected else TEXT_DIM)
            if key == self.active_key and not disabled:
                cy = y + row_height // 2
                draw.ellipse((SCREEN_SIZE - 30, cy - 6, SCREEN_SIZE - 18, cy + 6), fill=ACCENT)

        # Scrollbar on the right when the list overflows the visible window.
        if count > visible:
            bar_x0, bar_x1 = SCREEN_SIZE - 8, SCREEN_SIZE - 5
            bar_top = area_top
            bar_bottom = area_top + visible * (row_height + gap) - gap
            draw.rounded_rectangle((bar_x0, bar_top, bar_x1, bar_bottom), radius=1, fill=ROW_BG)
            track = bar_bottom - bar_top
            thumb = max(16, track * visible // count)
            thumb_top = min(bar_top + track * start // count, bar_bottom - thumb)
            draw.rounded_rectangle((bar_x0, thumb_top, bar_x1, thumb_top + thumb), radius=1, fill=ACCENT)

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


def main_menu(lang: str = "fr", selected: int = 0, mode: str | None = None) -> ListMenu:
    strings = MAIN_STRINGS.get(lang, MAIN_STRINGS["fr"])
    # "Alternance" only makes sense in the alternating mode; grey it out otherwise.
    disabled = frozenset() if mode == "velo_communauto" else frozenset({"rotate"})
    return ListMenu(
        title=strings["title"],
        options=list(strings["options"]),
        footer=strings["footer"],
        selected=selected,
        disabled_keys=disabled,
    )


@dataclass
class RotateScreen:
    """Horizontal picker for the alternation interval, stepping through ROTATE_OPTIONS.

    Adjusted with joystick left/right (hold to ramp), like the brightness screens.
    """

    seconds: int
    lang: str = "fr"

    def __post_init__(self) -> None:
        if self.seconds in ROTATE_OPTIONS:
            self.index = ROTATE_OPTIONS.index(self.seconds)
        else:  # snap a non-listed value to the nearest option
            self.index = min(range(len(ROTATE_OPTIONS)),
                             key=lambda i: abs(ROTATE_OPTIONS[i] - self.seconds))

    @property
    def value(self) -> int:
        return ROTATE_OPTIONS[self.index]

    def adjust(self, delta: int) -> None:
        self.index = max(0, min(len(ROTATE_OPTIONS) - 1, self.index + delta))

    def render(self, confirmed: bool = False) -> Image.Image:
        strings = ROTATE_STRINGS.get(self.lang, ROTATE_STRINGS["fr"])
        image = Image.new("RGB", (SCREEN_SIZE, SCREEN_SIZE), BG)
        draw = ImageDraw.Draw(image)

        draw.text((16, 12), strings["title"], font=_load_font(24), fill=TITLE)
        draw.line((16, 44, SCREEN_SIZE - 16, 44), fill=(60, 64, 72))

        big = _load_font(64)
        text = f"{self.value} {strings['unit']}"
        width = draw.textlength(text, font=big)
        draw.text(((SCREEN_SIZE - width) // 2, 66), text, font=big, fill=TITLE)

        # Position dots for the discrete choices.
        count = len(ROTATE_OPTIONS)
        gap = 26
        x0 = (SCREEN_SIZE - (count - 1) * gap) // 2
        cy = 170
        for i in range(count):
            cx = x0 + i * gap
            radius = 6 if i == self.index else 3
            draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius),
                         fill=ACCENT if i == self.index else ROW_BG)

        footer = strings["confirmed"] if confirmed else strings["footer"]
        draw.text((16, SCREEN_SIZE - 22), footer, font=_load_font(13),
                  fill=ACCENT if confirmed else TEXT_DIM)
        return image


def rotate_screen(lang: str = "fr", seconds: int = 10) -> RotateScreen:
    return RotateScreen(seconds=seconds, lang=lang)


@dataclass
class BrightnessScreen:
    """A 0-100 brightness adjuster (joystick left/right) with a level bar."""

    value: int
    lang: str = "fr"
    step: int = BRIGHTNESS_STEP
    title: str | None = None

    def __post_init__(self) -> None:
        self.value = _clamp(self.value)

    def adjust(self, delta: int) -> None:
        self.value = _clamp(self.value + delta * self.step)

    def render(self, confirmed: bool = False) -> Image.Image:
        strings = BRIGHTNESS_STRINGS.get(self.lang, BRIGHTNESS_STRINGS["fr"])
        image = Image.new("RGB", (SCREEN_SIZE, SCREEN_SIZE), BG)
        draw = ImageDraw.Draw(image)

        draw.text((16, 12), self.title or strings["title"], font=_load_font(24), fill=TITLE)
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
    """Evening-off editor: state + trigger (fixed time / sunset) + off time + on time.

    When ``sunset`` is on, the off time follows Montréal's sunset (resolved by the
    daemon); the off-time row then just shows the approximate ``sunset_label``.
    """

    enabled: bool
    off_minutes: int
    on_minutes: int
    lang: str = "fr"
    field: int = 0  # 0 = state, 1 = trigger, 2 = off time, 3 = on time
    sunset: bool = False
    sunset_label: str = ""
    sunrise_label: str = ""

    def move(self, delta: int) -> None:
        self.field = (self.field + delta) % 4

    def adjust(self, delta: int) -> None:
        if self.field == 0:
            self.enabled = not self.enabled
        elif self.field == 1:
            self.sunset = not self.sunset
        elif self.field == 2:
            if not self.sunset:  # times are fixed only when not following the sun
                self.off_minutes = (self.off_minutes + delta * TIME_STEP_MIN) % (24 * 60)
        elif self.field == 3:
            if not self.sunset:
                self.on_minutes = (self.on_minutes + delta * TIME_STEP_MIN) % (24 * 60)

    def render(self, confirmed: bool = False) -> Image.Image:
        strings = SLEEP_STRINGS.get(self.lang, SLEEP_STRINGS["fr"])
        image = Image.new("RGB", (SCREEN_SIZE, SCREEN_SIZE), BG)
        draw = ImageDraw.Draw(image)

        draw.text((16, 12), strings["title"], font=_load_font(24), fill=TITLE)
        draw.line((16, 44, SCREEN_SIZE - 16, 44), fill=(60, 64, 72))

        if self.sunset:
            off_value = self.sunset_label or strings["sunset"]
            on_value = self.sunrise_label or "—"
        else:
            off_value = minutes_to_hhmm(self.off_minutes)
            on_value = minutes_to_hhmm(self.on_minutes)
        rows = [
            (strings["enabled"], strings["on"] if self.enabled else strings["off"], False),
            (strings["trigger"], strings["sunset"] if self.sunset else strings["fixed"], False),
            (strings["off_at"], off_value, self.sunset),  # dim the value when following the sun
            (strings["on_at"], on_value, self.sunset),
        ]
        label_font = _load_font(16)
        value_font = _load_font(16)
        top, gap = 52, 6
        row_height = (SCREEN_SIZE - 26 - top - gap * (len(rows) - 1)) // len(rows)
        for index, (label, value, dim_value) in enumerate(rows):
            y = top + index * (row_height + gap)
            is_selected = index == self.field
            dim = (not self.enabled) and index > 0  # only the state row matters when disabled
            draw.rounded_rectangle(
                (12, y, SCREEN_SIZE - 12, y + row_height),
                radius=10,
                fill=ROW_BG_SELECTED if is_selected else ROW_BG,
            )
            vy = y + max(2, (row_height - 16) // 2)
            draw.text((22, vy), label, font=label_font,
                      fill=TITLE if is_selected else (TEXT_DIM if dim else TEXT))
            vw = draw.textlength(value, font=value_font)
            value_dim = dim or dim_value
            draw.text((SCREEN_SIZE - 24 - vw, vy), value, font=value_font,
                      fill=TITLE if is_selected else (TEXT_DIM if value_dim else ACCENT))

        footer = strings["confirmed"] if confirmed else strings["footer"]
        draw.text((16, SCREEN_SIZE - 22), footer, font=_load_font(12),
                  fill=ACCENT if confirmed else TEXT_DIM)
        return image


def sleep_screen(lang: str, enabled: bool, off_start: str, off_end: str,
                 sunset_label: str = "", sunrise_label: str = "") -> SleepScreen:
    sunset = str(off_start).strip().lower() == "sunset"
    return SleepScreen(
        enabled=enabled,
        off_minutes=21 * 60 if sunset else hhmm_to_minutes(off_start, 21 * 60),
        on_minutes=hhmm_to_minutes(off_end, 8 * 60),
        lang=lang,
        sunset=sunset,
        sunset_label=sunset_label,
        sunrise_label=sunrise_label,
    )


def _clip_to_width(draw: ImageDraw.ImageDraw, text: str, font, max_width: int) -> str:
    """Trim ``text`` (adding an ellipsis) until it fits ``max_width`` pixels."""
    if draw.textlength(text, font=font) <= max_width:
        return text
    while text and draw.textlength(text + "…", font=font) > max_width:
        text = text[:-1]
    return text + "…"


@dataclass
class InfoScreen:
    """A read-only list of label/value rows (device information)."""

    title: str
    rows: list[tuple[str, str]]  # (label, value)
    footer: str = ""

    def render(self, confirmed: bool = False) -> Image.Image:
        image = Image.new("RGB", (SCREEN_SIZE, SCREEN_SIZE), BG)
        draw = ImageDraw.Draw(image)

        draw.text((16, 12), self.title, font=_load_font(24), fill=TITLE)
        draw.line((16, 44, SCREEN_SIZE - 16, 44), fill=(60, 64, 72))

        label_font = _load_font(13)
        value_font = _load_font(14)
        top, bottom = 52, SCREEN_SIZE - 26
        count = max(1, len(self.rows))
        row_height = (bottom - top) // count
        value_x = 90  # narrower label column so a full IPv4 fits on the right
        for index, (label, value) in enumerate(self.rows):
            y = top + index * row_height
            draw.text((16, y), label, font=label_font, fill=TEXT_DIM)
            shown = _clip_to_width(draw, str(value), value_font, SCREEN_SIZE - 12 - value_x)
            draw.text((value_x, y), shown, font=value_font, fill=TEXT)

        if self.footer:
            draw.text((16, SCREEN_SIZE - 22), self.footer, font=_load_font(12), fill=TEXT_DIM)
        return image


def info_screen(lang: str, values: dict) -> InfoScreen:
    strings = INFO_STRINGS.get(lang, INFO_STRINGS["fr"])
    rows = [(label, str(values.get(key, "—"))) for key, label in strings["rows"]]
    return InfoScreen(title=strings["title"], rows=rows, footer=strings["footer"])
