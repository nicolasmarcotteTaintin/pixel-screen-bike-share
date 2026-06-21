"""The display loop: fetch live data, render a frame, push it to the Pixoo."""

from __future__ import annotations

import logging
import signal
import time
from pathlib import Path
from typing import Any

from PIL import Image

from . import pixoo
from .config import active_networks, load_config
from .providers.registry import get_provider
from .rendering import render
from .schedule import is_off_now
from .status import write_status
from .wifi import get_wifi_ssid

STOP_REQUESTED = False

# During quiet hours, re-assert screen-off this often (s) — the Pixoo self-wakes.
QUIET_POLL_SECONDS = 12.0


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
    screen_on: bool | None = None  # tracks panel power across frames for the quiet-hours window

    while not STOP_REQUESTED:
        config = load_config()
        pixoo_ip = config.get("pixoo_ip") or pixoo_ip or pixoo.discover_pixoo()
        if not pixoo_ip and not preview_path:
            logging.error("Pixoo IP unavailable. Set PIXOO_IP or add pixoo_ip to config.json.")

        # Quiet hours: keep the panel off and skip all network/render work (including
        # set_brightness, which would wake the panel) until the window ends. The Pixoo
        # firmware re-wakes itself after a while, so re-assert "off" on every poll.
        if not once and is_off_now(config):
            if pixoo_ip:
                try:
                    pixoo.set_screen(pixoo_ip, False, timeout=3, retries=1)
                    if screen_on is not False:
                        logging.info("Quiet hours: Pixoo screen off")
                except Exception as exc:
                    if screen_on is not False:
                        logging.warning("Could not turn Pixoo screen off: %s", exc)
                screen_on = False
            _sleep_interruptibly(QUIET_POLL_SECONDS)
            continue
        if screen_on is False and pixoo_ip:
            try:
                pixoo.set_screen(pixoo_ip, True, timeout=3, retries=1)
                logging.info("Quiet hours over: Pixoo screen on")
            except Exception as exc:
                logging.warning("Could not turn Pixoo screen on: %s", exc)
        screen_on = True

        # Refresh the slow-moving data once per cycle, for every active network in
        # the mode (one for "velo"/"communauto", two for "velo_communauto").
        active = active_networks(config)
        rotate_seconds = config["rotate_seconds"]
        data_error = ""
        rendered: list[tuple[Any, Any]] = []  # (provider, view) pairs that fetched OK
        for name in active:
            provider = get_provider(name)
            try:
                rendered.append((provider, provider.fetch(config)))
            except Exception as exc:
                logging.exception("Data refresh failed for network %s", name)
                data_error = str(exc)
        ssid = get_wifi_ssid()
        if pixoo_ip:
            try:
                pixoo.set_brightness(pixoo_ip, config["brightness"])
            except Exception as exc:
                logging.warning("Could not set Pixoo brightness: %s", exc)

        # Push a frame every second so the clock colon blinks, rotating between the
        # active networks on a wall-clock cadence, until it's time to refresh data.
        deadline = time.monotonic() + config["refresh_seconds"]
        sent = skipped = 0
        last_error = ""
        view: Any = rendered[0][1] if rendered else None
        while not STOP_REQUESTED:
            # When the quiet-hours window opens mid-cycle, break back to the outer
            # loop, which turns the panel off before any further work.
            if not once and is_off_now(config):
                break

            if len(rendered) > 1:
                index = int(time.time() // rotate_seconds) % len(rendered)
                provider, view = rendered[index]
            elif rendered:
                provider, view = rendered[0]

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
                    _snapshot(config, active, pixoo_ip, pixoo_ok, ssid, view, sent, skipped, last_error, data_error)

            if once:
                _snapshot(config, active, pixoo_ip, pixoo_ok, ssid, view, sent, skipped, last_error, data_error)
                return
            _sleep_interruptibly(max(0.05, 1.0 - (time.time() % 1.0)))
            if time.monotonic() >= deadline:
                break

        logging.info(
            "cycle: mode=%s networks=%s ssid=%s pixoo=%s ok=%s sent=%d skipped=%d%s",
            config["mode"], "+".join(active), ssid, pixoo_ip, pixoo_ok, sent, skipped,
            f" data_error={data_error}" if data_error else "",
        )
        _snapshot(config, active, pixoo_ip, pixoo_ok, ssid, view, sent, skipped, last_error, data_error)


def _blank() -> Image.Image:
    return Image.new("RGB", (64, 64), "black")


def _row_count(view: Any) -> int:
    return len(getattr(view, "rows", []) or [])


def _snapshot(
    config: dict[str, Any],
    active: list[str],
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
        mode=config["mode"],
        networks="+".join(active),
        pixoo_ip=pixoo_ip,
        pixoo_ok=pixoo_ok,
        ssid=ssid,
        rows=_row_count(view),
        frames_sent=sent,
        frames_skipped=skipped,
        last_pixoo_error=last_error,
        data_error=data_error,
    )
