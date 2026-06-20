"""The display loop: fetch live data, render a frame, push it to the Pixoo."""

from __future__ import annotations

import logging
import signal
import time
from pathlib import Path
from typing import Any

from PIL import Image

from . import pixoo
from .config import load_config
from .providers.registry import get_provider
from .rendering import render
from .status import write_status
from .wifi import get_wifi_ssid

STOP_REQUESTED = False


def register_signal_handlers() -> None:
    def stop(signum: int, frame: object) -> None:
        global STOP_REQUESTED
        STOP_REQUESTED = True
        logging.info("Stop requested by signal %s", signum)

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)


def _sleep_interruptibly(seconds: float) -> None:
    deadline = time.monotonic() + seconds
    while not STOP_REQUESTED and time.monotonic() < deadline:
        time.sleep(min(1, deadline - time.monotonic()))


def run_display_loop(once: bool = False, preview_path: Path | None = None) -> None:
    pixoo_ip: str | None = None
    view: Any = None
    ssid: str | None = None
    pixoo_ok: bool | None = None  # tracks Pixoo reachability across frames for edge-triggered logging

    while not STOP_REQUESTED:
        # Refresh the slow-moving data once per cycle.
        config = load_config()
        provider = get_provider(config["network"])
        pixoo_ip = config.get("pixoo_ip") or pixoo_ip or pixoo.discover_pixoo()
        if not pixoo_ip and not preview_path:
            logging.error("Pixoo IP unavailable. Set PIXOO_IP or add pixoo_ip to config.json.")

        data_error = ""
        try:
            view = provider.fetch(config)
            ssid = get_wifi_ssid()
        except Exception as exc:
            logging.exception("Data refresh failed for network %s", config["network"])
            data_error = str(exc)
        if pixoo_ip:
            try:
                pixoo.set_brightness(pixoo_ip, config["brightness"])
            except Exception as exc:
                logging.warning("Could not set Pixoo brightness: %s", exc)

        # Push a frame every second so the clock colon blinks, until it's time to refresh data.
        deadline = time.monotonic() + config["refresh_seconds"]
        sent = skipped = 0
        last_error = ""
        while not STOP_REQUESTED:
            try:
                image = render(view, provider) if view is not None else _blank()
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
                # Log + snapshot only on a reachability change (down<->up): quiet but precise.
                if new_ok != pixoo_ok:
                    if new_ok:
                        logging.info("Pixoo reachable at %s", pixoo_ip)
                    else:
                        logging.warning("Pixoo unreachable at %s: %s", pixoo_ip, last_error)
                    pixoo_ok = new_ok
                    _snapshot(config, pixoo_ip, pixoo_ok, ssid, view, sent, skipped, last_error, data_error)

            if once:
                _snapshot(config, pixoo_ip, pixoo_ok, ssid, view, sent, skipped, last_error, data_error)
                return
            _sleep_interruptibly(max(0.05, 1.0 - (time.time() % 1.0)))
            if time.monotonic() >= deadline:
                break

        logging.info(
            "cycle: network=%s rows=%d ssid=%s pixoo=%s ok=%s sent=%d skipped=%d%s",
            config["network"], _row_count(view), ssid, pixoo_ip, pixoo_ok, sent, skipped,
            f" data_error={data_error}" if data_error else "",
        )
        _snapshot(config, pixoo_ip, pixoo_ok, ssid, view, sent, skipped, last_error, data_error)


def _blank() -> Image.Image:
    return Image.new("RGB", (64, 64), "black")


def _row_count(view: Any) -> int:
    return len(getattr(view, "rows", []) or [])


def _snapshot(
    config: dict[str, Any],
    pixoo_ip: str | None,
    pixoo_ok: bool | None,
    ssid: str | None,
    view: Any,
    sent: int,
    skipped: int,
    last_error: str,
    data_error: str,
) -> None:
    write_status(
        network=config["network"],
        pixoo_ip=pixoo_ip,
        pixoo_ok=pixoo_ok,
        ssid=ssid,
        rows=_row_count(view),
        frames_sent=sent,
        frames_skipped=skipped,
        last_pixoo_error=last_error,
        data_error=data_error,
    )
