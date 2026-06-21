from __future__ import annotations

import base64
import json
import logging
import os
import socket
import time
from typing import Any

import requests
from PIL import Image
from zeroconf import ServiceBrowser, ServiceInfo, Zeroconf


PIXOO_PORT = 80
PIXOO_POST_PATH = "/post"
REQUEST_TIMEOUT_SECONDS = 5
REQUEST_RETRIES = 3
HTTP_GIF_ID_LIMIT = 32


class PixooError(RuntimeError):
    """Raised when the Pixoo LAN API cannot complete a command."""


def discover_pixoo(timeout: float = 5.0) -> str | None:
    """Discover a Pixoo/Divoom device advertised through zeroconf."""

    env_ip = os.getenv("PIXOO_IP")
    if env_ip:
        logging.info("Using Pixoo IP from PIXOO_IP=%s", env_ip)
        return env_ip

    matches: list[str] = []

    class PixooListener:
        def add_service(self, zeroconf: Zeroconf, service_type: str, name: str) -> None:
            self._handle_service(zeroconf, service_type, name)

        def update_service(self, zeroconf: Zeroconf, service_type: str, name: str) -> None:
            self._handle_service(zeroconf, service_type, name)

        def remove_service(self, zeroconf: Zeroconf, service_type: str, name: str) -> None:
            return None

        def _handle_service(self, zeroconf: Zeroconf, service_type: str, name: str) -> None:
            info = zeroconf.get_service_info(service_type, name, timeout=1000)
            if not info:
                return
            label = _service_label(name, info)
            if "pixoo" not in label and "divoom" not in label:
                return
            for ip in _service_addresses(info):
                if ip not in matches:
                    matches.append(ip)
                    logging.info("Pixoo candidate discovered by zeroconf: %s (%s)", ip, name)

    zeroconf = Zeroconf()
    browsers: list[ServiceBrowser] = []
    try:
        listener = PixooListener()
        for service_type in ("_http._tcp.local.", "_divoom._tcp.local.", "_pixoo._tcp.local."):
            try:
                browsers.append(ServiceBrowser(zeroconf, service_type, listener))
            except Exception as exc:
                logging.debug("Could not browse zeroconf service %s: %s", service_type, exc)

        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline and not matches:
            time.sleep(0.2)
    finally:
        zeroconf.close()

    if matches:
        return matches[0]

    logging.warning("No Pixoo found through zeroconf")
    return None


def send_image(
    ip: str,
    image: Image.Image,
    *,
    timeout: float = REQUEST_TIMEOUT_SECONDS,
    retries: int = REQUEST_RETRIES,
    reset_on_error: bool = True,
) -> dict[str, Any]:
    """Convert a Pillow image to Pixoo RGB payload and push it over HTTP."""

    frame = image.convert("RGB").resize((64, 64), Image.Resampling.NEAREST)
    pic_id = _next_pic_id(ip, timeout=timeout, retries=retries, reset_on_error=reset_on_error)
    payload = {
        "Command": "Draw/SendHttpGif",
        "PicNum": 1,
        "PicWidth": 64,
        "PicOffset": 0,
        "PicID": pic_id,
        "PicSpeed": 1000,
        "PicData": base64.b64encode(frame.tobytes("raw", "RGB")).decode("ascii"),
    }
    return _post_command(ip, payload, timeout=timeout, retries=retries)


def set_brightness(ip: str, brightness: int) -> dict[str, Any]:
    brightness = max(0, min(100, int(brightness)))
    return _post_command(
        ip,
        {
            "Command": "Channel/SetBrightness",
            "Brightness": brightness,
        },
    )


def set_screen(ip: str, on: bool, **kwargs: Any) -> dict[str, Any]:
    """Turn the Pixoo panel on or off (Channel/OnOffScreen)."""
    return _post_command(
        ip,
        {
            "Command": "Channel/OnOffScreen",
            "OnOff": 1 if on else 0,
        },
        **kwargs,
    )


def _next_pic_id(
    ip: str,
    *,
    timeout: float = REQUEST_TIMEOUT_SECONDS,
    retries: int = REQUEST_RETRIES,
    reset_on_error: bool = True,
) -> int:
    try:
        response = _post_command(ip, {"Command": "Draw/GetHttpGifId"}, timeout=timeout, retries=retries)
        pic_id = int(response.get("PicId", 0)) + 1
    except Exception as exc:
        if not reset_on_error:
            raise
        logging.warning("Could not read Pixoo GIF id, resetting counter: %s", exc)
        _post_command(ip, {"Command": "Draw/ResetHttpGifId"}, timeout=timeout, retries=retries)
        pic_id = 1

    if pic_id >= HTTP_GIF_ID_LIMIT:
        _post_command(ip, {"Command": "Draw/ResetHttpGifId"}, timeout=timeout, retries=retries)
        pic_id = 1
    return pic_id


def _post_command(
    ip: str,
    payload: dict[str, Any],
    *,
    timeout: float = REQUEST_TIMEOUT_SECONDS,
    retries: int = REQUEST_RETRIES,
) -> dict[str, Any]:
    url = f"http://{ip}:{PIXOO_PORT}{PIXOO_POST_PATH}"
    last_error: Exception | None = None

    for attempt in range(1, retries + 1):
        try:
            response = requests.post(
                url,
                data=json.dumps(payload),
                headers={"Content-Type": "application/json"},
                timeout=timeout,
            )
            response.raise_for_status()
            data = response.json()
            if int(data.get("error_code", 0)) != 0:
                raise PixooError(f"Pixoo command failed: {data}")
            return data
        except (requests.RequestException, ValueError, PixooError) as exc:
            last_error = exc
            logging.warning(
                "Pixoo command %s failed on attempt %s/%s: %s",
                payload.get("Command"),
                attempt,
                retries,
                exc,
            )
            if attempt < retries:
                time.sleep(0.5 * attempt)

    raise PixooError(f"Pixoo command failed after {retries} attempts: {last_error}")


def _service_label(name: str, info: ServiceInfo) -> str:
    parts = [name, info.server or ""]
    for key, value in info.properties.items():
        try:
            parts.append(key.decode("utf-8", errors="ignore"))
            parts.append(value.decode("utf-8", errors="ignore"))
        except AttributeError:
            parts.append(str(key))
            parts.append(str(value))
    return " ".join(parts).lower()


def _service_addresses(info: ServiceInfo) -> list[str]:
    if hasattr(info, "parsed_addresses"):
        return [address for address in info.parsed_addresses() if "." in address]

    addresses = []
    for packed in info.addresses:
        try:
            addresses.append(socket.inet_ntoa(packed))
        except OSError:
            continue
    return addresses
