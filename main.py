from __future__ import annotations

import argparse
import json
import logging
import os
import signal
import subprocess
import sys
import time
import unicodedata
from html import escape
from pathlib import Path
from typing import Any

import requests
from flask import Flask, redirect, request
from PIL import Image, ImageDraw

import pixoo


BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = Path(os.getenv("BIXI_CONFIG_PATH", BASE_DIR / "config.json"))
LOG_PATH = Path(os.getenv("BIXI_LOG_PATH", "/var/log/bixi-display.log"))
LOGO_PATH = Path(os.getenv("BIXI_LOGO_PATH", BASE_DIR / "Bixi_logo2_27.png"))
STATUS_PATH = Path(os.getenv("BIXI_STATUS_PATH", BASE_DIR / "status.json"))

STATION_INFORMATION_URL = "https://gbfs.velobixi.com/gbfs/en/station_information.json"
STATION_STATUS_URL = "https://gbfs.velobixi.com/gbfs/en/station_status.json"

REQUEST_TIMEOUT_SECONDS = 5
REQUEST_RETRIES = 3
DEFAULT_CONFIG = {
    "favorite_stations": ["6026", "6174", "6100"],
    "refresh_seconds": 60,
    "brightness": 80,
}

STOP_REQUESTED = False


def main() -> int:
    parser = argparse.ArgumentParser(description="Display live BIXI station status on a Pixoo 64.")
    parser.add_argument("--setup", action="store_true", help="Run the local Flask setup server.")
    parser.add_argument("--once", action="store_true", help="Render and send one frame, then exit.")
    parser.add_argument("--preview", type=Path, help="Write the rendered 64x64 image to this PNG path.")
    args = parser.parse_args()

    setup_logging()
    ensure_config_exists()

    if args.setup:
        run_setup_server()
        return 0

    register_signal_handlers()
    run_display_loop(once=args.once, preview_path=args.preview)
    return 0


def setup_logging() -> None:
    handlers: list[logging.Handler] = [logging.StreamHandler()]
    try:
        handlers.append(logging.FileHandler(LOG_PATH))
    except OSError as exc:
        fallback = BASE_DIR / "bixi-display.log"
        handlers.append(logging.FileHandler(fallback))
        print(f"Could not write {LOG_PATH}: {exc}. Logging to {fallback}", file=sys.stderr)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=handlers,
    )


def ensure_config_exists() -> None:
    if not CONFIG_PATH.exists():
        save_config(DEFAULT_CONFIG)


def load_config() -> dict[str, Any]:
    with CONFIG_PATH.open("r", encoding="utf-8") as file:
        config = json.load(file)
    merged = DEFAULT_CONFIG | config
    merged["favorite_stations"] = [str(station_id) for station_id in merged["favorite_stations"]]
    merged["refresh_seconds"] = max(10, int(merged["refresh_seconds"]))
    merged["brightness"] = max(0, min(100, int(merged["brightness"])))
    return merged


def save_config(config: dict[str, Any]) -> None:
    CONFIG_PATH.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")


def write_status(**fields: Any) -> None:
    """Write a one-glance health snapshot to STATUS_PATH (cat it to diagnose quickly)."""
    fields["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    try:
        STATUS_PATH.write_text(json.dumps(fields, indent=2) + "\n", encoding="utf-8")
    except OSError as exc:
        logging.debug("Could not write status file %s: %s", STATUS_PATH, exc)


def run_display_loop(once: bool = False, preview_path: Path | None = None) -> None:
    pixoo_ip: str | None = None
    stations: list[dict[str, Any]] = []
    ssid: str | None = None
    pixoo_ok: bool | None = None  # tracks Pixoo reachability across frames for edge-triggered logging

    while not STOP_REQUESTED:
        # Refresh the slow-moving data (BIXI status, Wi-Fi SSID) once per cycle.
        config = load_config()
        pixoo_ip = config.get("pixoo_ip") or pixoo_ip or pixoo.discover_pixoo()
        if not pixoo_ip and not preview_path:
            logging.error("Pixoo IP unavailable. Set PIXOO_IP or add pixoo_ip to config.json.")

        stations_error = ""
        try:
            stations = load_bixi_stations(config["favorite_stations"])
            ssid = get_wifi_ssid()
        except Exception as exc:
            logging.exception("Station data refresh failed")
            stations_error = str(exc)
        if pixoo_ip:
            try:
                pixoo.set_brightness(pixoo_ip, config["brightness"])
            except Exception as exc:
                logging.warning("Could not set Pixoo brightness: %s", exc)

        # Push a frame every few seconds so the clock colon blinks, until it's time to refresh data.
        deadline = time.monotonic() + config["refresh_seconds"]
        sent = skipped = 0
        last_error = ""
        while not STOP_REQUESTED:
            try:
                image = render_station_image(stations, ssid)
            except Exception:
                logging.exception("Render failed")
                image = None

            if image is not None and preview_path:
                image.save(preview_path)
            if image is not None and pixoo_ip:
                try:
                    # Best-effort: short timeout, no retries, so a slow/hung Pixoo never blocks the loop.
                    pixoo.send_image(pixoo_ip, image, timeout=3, retries=1, reset_on_error=False)
                    sent += 1
                    new_ok = True
                except Exception as exc:
                    skipped += 1
                    last_error = str(exc)
                    new_ok = False
                # Log + snapshot only on a reachability change (down<->up), so it's quiet but precise.
                if new_ok != pixoo_ok:
                    if new_ok:
                        logging.info("Pixoo reachable at %s", pixoo_ip)
                    else:
                        logging.warning("Pixoo unreachable at %s: %s", pixoo_ip, last_error)
                    pixoo_ok = new_ok
                    write_status(pixoo_ip=pixoo_ip, pixoo_ok=pixoo_ok, ssid=ssid,
                                 stations=len(stations), frames_sent=sent, frames_skipped=skipped,
                                 last_pixoo_error=last_error, stations_error=stations_error)

            if once:
                write_status(pixoo_ip=pixoo_ip, pixoo_ok=pixoo_ok, ssid=ssid,
                             stations=len(stations), frames_sent=sent, frames_skipped=skipped,
                             last_pixoo_error=last_error, stations_error=stations_error)
                return
            sleep_interruptibly(max(0.05, 1.0 - (time.time() % 1.0)))
            if time.monotonic() >= deadline:
                break

        # One concise heartbeat per data-refresh cycle, plus a snapshot for quick diagnosis.
        logging.info(
            "cycle: stations=%d ssid=%s pixoo=%s ok=%s sent=%d skipped=%d%s",
            len(stations), ssid, pixoo_ip, pixoo_ok, sent, skipped,
            f" stations_error={stations_error}" if stations_error else "",
        )
        write_status(pixoo_ip=pixoo_ip, pixoo_ok=pixoo_ok, ssid=ssid,
                     stations=len(stations), frames_sent=sent, frames_skipped=skipped,
                     last_pixoo_error=last_error, stations_error=stations_error)


def load_bixi_stations(favorite_station_ids: list[str]) -> list[dict[str, Any]]:
    information = fetch_gbfs(STATION_INFORMATION_URL).get("data", {}).get("stations", [])
    statuses = fetch_gbfs(STATION_STATUS_URL).get("data", {}).get("stations", [])

    by_id: dict[str, dict[str, Any]] = {}
    for station in information:
        station_id = str(station.get("station_id", ""))
        if station_id:
            by_id[station_id] = station.copy()

    for status in statuses:
        station_id = str(status.get("station_id", ""))
        if not station_id:
            continue
        by_id.setdefault(station_id, {})["station_id"] = station_id
        by_id[station_id].update(status)

    lookup: dict[str, dict[str, Any]] = {}
    for station in by_id.values():
        station_id = str(station.get("station_id", ""))
        short_name = str(station.get("short_name", ""))
        if station_id:
            lookup[station_id] = station
        if short_name:
            lookup[short_name] = station

    selected = []
    for favorite_id in favorite_station_ids:
        station = lookup.get(str(favorite_id))
        if station:
            selected.append(station)
        else:
            logging.warning("Favorite station %s was not found in GBFS data", favorite_id)
    return selected


def fetch_gbfs(url: str) -> dict[str, Any]:
    last_error: Exception | None = None
    for attempt in range(1, REQUEST_RETRIES + 1):
        try:
            response = requests.get(url, timeout=REQUEST_TIMEOUT_SECONDS)
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, ValueError) as exc:
            last_error = exc
            logging.warning("GBFS fetch failed on attempt %s/%s: %s", attempt, REQUEST_RETRIES, exc)
            if attempt < REQUEST_RETRIES:
                time.sleep(0.5 * attempt)
    raise RuntimeError(f"GBFS fetch failed after {REQUEST_RETRIES} attempts: {last_error}")


def render_station_image(stations: list[dict[str, Any]], ssid: str | None = None) -> Image.Image:
    image = Image.new("RGB", (64, 64), "black")
    draw = ImageDraw.Draw(image)
    content_top = 12

    rows = stations[:3]
    row_height = 3 + FONT_4X6_HEIGHT + 3  # 3px above the text + 6px text + 3px below
    # Rows anchored to the bottom edge; the pale blue header band absorbs the extra space.
    rows_top = 64 - len(rows) * row_height if rows else content_top + 11
    header_bottom = rows_top

    # Header band (column icons). The square logo overlaps its left side, where there is no text.
    # Band top is lowered 5px below content_top, leaving more black room for the clock.
    draw.rectangle((0, content_top + 5, 63, header_bottom - 1), fill=HEADER_BG)

    if not stations:
        no_data = "NO DATA"
        x = max(0, (64 - small_text_width(no_data)) // 2)
        y = header_bottom + max(0, (64 - header_bottom - FONT_5X7_HEIGHT) // 2)
        draw_small_text(draw, x, y, no_data, (255, 80, 80))
        draw_top_bar(image, draw)
        return image

    draw_table_header(draw, content_top + 7)

    for index, station in enumerate(rows):
        y = rows_top + index * row_height
        draw.rectangle((0, y, 63, y + row_height - 1), fill=ROW_BG[index % len(ROW_BG)])
        draw_station_table_row(draw, station, y, row_height, index)

    # Logo + clock drawn last so the logo sits on top of the header band's left side.
    draw_top_bar(image, draw)
    return image


# Column layout for the table: (icon key, color, number right edge x (exclusive), icon center x).
# The park column ends at 64 so its last pixel is column 63 (full width, no right margin).
TABLE_COLUMNS = [
    ("bike", (76, 235, 115), 44, 40),
    ("bolt", (255, 224, 64), 54, 51),
    ("park", (96, 184, 255), 64, 60),
]
NAME_MAX_WIDTH = 36

# Slightly different name tint per row to tell them apart.
NAME_TINTS = [
    (255, 255, 255),
    (200, 224, 255),
    (255, 224, 200),
]

# Row background bands: alternating dark greys for the stations, a strong header band (Excel-style).
HEADER_BG = (34, 78, 120)
ROW_BG = [(50, 50, 56), (18, 18, 20)]


def draw_table_header(draw: ImageDraw.ImageDraw, y: int) -> None:
    for key, color, _right, center_x in TABLE_COLUMNS:
        if key == "bike":
            draw_bike_icon(draw, center_x - 6, y, color)
        elif key == "bolt":
            draw_bolt_icon(draw, center_x - 2, y + 1, color)
        elif key == "park":
            draw_tiny_text(draw, center_x - 2, y + 1, "P", color)


def draw_clock(draw: ImageDraw.ImageDraw, x: int, y: int) -> None:
    color = (210, 210, 210)
    now = time.localtime()
    hours = f"{now.tm_hour:02d}"
    minutes = f"{now.tm_min:02d}"

    draw_small_text(draw, x, y, hours, color)
    # 1px-wide colon with a single free column on each side, toggling every second.
    colon_x = x + len(hours) * (FONT_5X7_WIDTH + 1)
    if int(time.time()) % 2 == 0:
        draw.point((colon_x, y + 2), fill=color)
        draw.point((colon_x, y + 4), fill=color)
    draw_small_text(draw, colon_x + 2, y, minutes, color)


def draw_station_table_row(
    draw: ImageDraw.ImageDraw,
    station: dict[str, Any],
    y: int,
    row_height: int,
    row_index: int,
) -> None:
    name = clip_station_name(
        station_name_label(str(station.get("name", station.get("station_id", "")))),
        NAME_MAX_WIDTH,
    )
    name_y = y + max(0, (row_height - FONT_4X6_HEIGHT) // 2)
    draw_station_name(draw, 0, name_y, name, NAME_TINTS[row_index % len(NAME_TINTS)])

    values = [
        int(station.get("num_bikes_available", 0) or 0),
        count_ebikes(station),
        int(station.get("num_docks_available", 0) or 0),
    ]
    number_y = y + max(0, (row_height - FONT_4X6_HEIGHT) // 2)
    for (_key, color, right, center_x), value in zip(TABLE_COLUMNS, values):
        text = clipped_metric(value)
        width = tiny_text_width(text)
        if len(text) == 1:
            number_x = center_x - width // 2  # single digit: centre it under its column icon
        else:
            number_x = right - width          # multi-digit: right-aligned to the column edge
        draw_tiny_text(draw, number_x, number_y, text, color)


def count_ebikes(station: dict[str, Any]) -> int:
    direct = station.get("num_ebikes_available")
    if direct is not None:
        return int(direct or 0)

    total = 0
    bike_types = station.get("num_bikes_available_types") or station.get("vehicle_types_available") or []
    if isinstance(bike_types, dict):
        bike_types = [bike_types]
    for item in bike_types:
        if not isinstance(item, dict):
            continue
        for key in ("ebike", "electric", "electric_bike"):
            if key in item:
                total += int(item[key] or 0)
        if str(item.get("vehicle_type_id", "")).lower() in {"ebike", "electric", "electric_bike"}:
            total += int(item.get("count", 0) or 0)
    return total


STREET_ABBREVIATIONS = {
    "AVENUE": "AVE",
    "AV": "AVE",
    "BOULEVARD": "BOUL",
    "RUE": "",
    "CHEMIN": "CH",
    "SAINT": "ST",
    "SAINTE": "STE",
    "STREET": "ST",
    "PLACE": "PL",
    # Specific long name shortened to fit the narrow column.
    "MONT-ROYAL": "MONT-R",
    # Prepositions dropped so the meaningful street name shows (e.g. "du Mont-Royal" -> "MONT-R").
    "DU": "",
    "DE": "",
    "DES": "",
}


def _abbreviate_part(part: str) -> str:
    words = [STREET_ABBREVIATIONS.get(word, word) for word in part.upper().split()]
    return " ".join(word for word in words if word)


def station_name_label(name: str) -> str:
    """Abbreviated ASCII uppercase label from the first part of the name (before '/')."""
    normalized = unicodedata.normalize("NFKD", name)
    ascii_name = normalized.encode("ascii", "ignore").decode("ascii")
    return _abbreviate_part(ascii_name.split("/")[0]) or "BIXI"


# 3x4 superscript glyphs for French ordinal suffixes (e.g. 2e, 1er, 1re).
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
    """Draw a 5x7 name, rendering ordinal letters that follow a digit as small superscripts."""
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


def clip_station_name(text: str, max_width: int) -> str:
    while text and station_name_width(text) > max_width:
        text = text[:-1]
    return text


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
    "B": ("110", "101", "110", "101", "110"),
    "E": ("111", "100", "110", "100", "111"),
    "I": ("111", "010", "010", "010", "111"),
    "P": ("110", "101", "110", "100", "100"),
    "X": ("101", "101", "010", "101", "101"),
}


# 5x7 pixel font (5 wide, 7 tall) used for every text except the BIXI logo.
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


_LOGO_CACHE: Image.Image | None | bool = None


def load_logo() -> Image.Image | None:
    global _LOGO_CACHE
    if _LOGO_CACHE is None:
        try:
            _LOGO_CACHE = Image.open(LOGO_PATH).convert("RGBA")
        except OSError:
            logging.warning("Logo image %s unavailable, falling back to text logo", LOGO_PATH)
            _LOGO_CACHE = False
    return _LOGO_CACHE or None


def get_wifi_ssid() -> str | None:
    """Return the connected Wi-Fi SSID, or None if not connected."""
    commands = [
        ["iwgetid", "-r"],
        ["nmcli", "-t", "-f", "active,ssid", "dev", "wifi"],
        ["networksetup", "-getairportnetwork", "en0"],
    ]
    for command in commands:
        try:
            output = subprocess.run(
                command, capture_output=True, text=True, timeout=3
            ).stdout.strip()
        except (OSError, subprocess.SubprocessError):
            continue
        if not output:
            continue
        if command[0] == "iwgetid":
            return output
        if command[0] == "nmcli":
            for line in output.splitlines():
                if line.startswith("yes:"):
                    ssid = line.split(":", 1)[1].strip()
                    if ssid:
                        return ssid
            continue
        if command[0] == "networksetup":
            marker = "Current Wi-Fi Network: "
            if output.startswith(marker):
                return output[len(marker):].strip()
    return None


def draw_top_bar(image: Image.Image, draw: ImageDraw.ImageDraw) -> None:
    logo = load_logo()
    if logo is not None:
        logo_x = 1
        image.paste(logo, (logo_x, 0), logo)
        logo_right = logo_x + logo.width
    else:
        draw_pixel_text(draw, 0, 0, "BIXI", (245, 245, 245), scale=2)
        logo_right = pixel_text_width("BIXI", scale=2)

    # Clock to the right of the logo, in the clear strip above the header band.
    draw_clock(draw, logo_right + 10, 3)


# 4x6 font (4 wide, 6 tall): metric counters and station names (same size).
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


def clipped_metric(value: int) -> str:
    return "99" if value > 99 else str(max(0, value))


def draw_bike_icon(draw: ImageDraw.ImageDraw, x: int, y: int, color: tuple[int, int, int]) -> None:
    # 13x7 BIXI-style step-through city bike: low open frame, upright seat and handlebar.
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


def run_setup_server() -> None:
    app = Flask(__name__)

    @app.get("/")
    def index() -> str:
        config = load_config()
        stations = "\n".join(config["favorite_stations"])
        message = escape(request.args.get("saved", ""))
        refresh_seconds = config["refresh_seconds"]
        brightness = config["brightness"]
        return f"""<!doctype html>
<html lang="fr">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>BIXI Pixoo setup</title>
  <style>
    body {{ background: #111; color: #f5f5f5; font-family: system-ui, sans-serif; margin: 2rem; }}
    main {{ max-width: 36rem; margin: auto; }}
    label {{ display: block; margin-top: 1rem; font-weight: 700; }}
    textarea, input {{ box-sizing: border-box; width: 100%; padding: .7rem; margin-top: .35rem; border: 1px solid #555; border-radius: 8px; background: #1f1f1f; color: white; }}
    button {{ margin-top: 1.25rem; padding: .8rem 1rem; border: 0; border-radius: 8px; background: #38a169; color: white; font-weight: 700; }}
    .saved {{ color: #68d391; min-height: 1.5rem; }}
  </style>
</head>
<body>
  <main>
    <h1>BIXI Pixoo</h1>
    <p class="saved">{message}</p>
    <form method="post">
      <label for="favorite_stations">Stations favorites, une par ligne (station_id ou short_name)</label>
      <textarea id="favorite_stations" name="favorite_stations" rows="6">{escape(stations)}</textarea>

      <label for="refresh_seconds">Rafraichissement, secondes</label>
      <input id="refresh_seconds" name="refresh_seconds" type="number" min="10" max="3600" value="{refresh_seconds}">

      <label for="brightness">Luminosite, 0 a 100</label>
      <input id="brightness" name="brightness" type="number" min="0" max="100" value="{brightness}">

      <button type="submit">Sauvegarder</button>
    </form>
  </main>
</body>
</html>"""

    @app.post("/")
    def save() -> Any:
        stations = [
            line.strip()
            for line in request.form.get("favorite_stations", "").splitlines()
            if line.strip()
        ]
        config = load_config()
        config["favorite_stations"] = stations
        config["refresh_seconds"] = max(10, min(3600, int(request.form.get("refresh_seconds", 60))))
        config["brightness"] = max(0, min(100, int(request.form.get("brightness", 80))))
        save_config(config)
        logging.info("Configuration saved from setup server")
        return redirect("/?saved=Configuration%20sauvegardee")

    app.run(host="0.0.0.0", port=8080)


def register_signal_handlers() -> None:
    def stop(signum: int, frame: object) -> None:
        global STOP_REQUESTED
        STOP_REQUESTED = True
        logging.info("Stop requested by signal %s", signum)

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)


def sleep_interruptibly(seconds: float) -> None:
    deadline = time.monotonic() + seconds
    while not STOP_REQUESTED and time.monotonic() < deadline:
        time.sleep(min(1, deadline - time.monotonic()))


if __name__ == "__main__":
    raise SystemExit(main())
