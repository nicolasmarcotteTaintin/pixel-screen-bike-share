"""Minimal ST7789 driver for the Waveshare 1.3" 240x240 IPS LCD (HAT).

SPI + a few GPIO lines (reset, data/command, backlight). The hardware libraries
(``spidev``, ``RPi.GPIO``) are imported lazily inside :meth:`ST7789.__init__`, so
this module can be imported on any machine; only constructing the driver requires
a Raspberry Pi.

Default pin map (BCM) matches the Waveshare 1.3inch LCD HAT.
"""

from __future__ import annotations

import time

from PIL import Image

WIDTH = 240
HEIGHT = 240

# Waveshare 1.3" LCD HAT pin map (BCM numbering).
PIN_RST = 27
PIN_DC = 25
PIN_BL = 24
SPI_BUS = 0
SPI_DEVICE = 0
SPI_HZ = 40_000_000


class ST7789:
    def __init__(
        self,
        *,
        rst: int = PIN_RST,
        dc: int = PIN_DC,
        bl: int = PIN_BL,
        spi_bus: int = SPI_BUS,
        spi_device: int = SPI_DEVICE,
        spi_hz: int = SPI_HZ,
    ) -> None:
        import spidev  # noqa: PLC0415 — lazy, Pi-only
        import RPi.GPIO as GPIO  # noqa: PLC0415 — lazy, Pi-only

        self._gpio = GPIO
        self._rst, self._dc, self._bl = rst, dc, bl

        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        for pin in (rst, dc, bl):
            GPIO.setup(pin, GPIO.OUT)
        GPIO.output(bl, GPIO.HIGH)  # backlight on

        self._spi = spidev.SpiDev()
        self._spi.open(spi_bus, spi_device)
        self._spi.max_speed_hz = spi_hz
        self._spi.mode = 0

        self._init_display()

    # --- low-level ---------------------------------------------------------

    def _command(self, data: int) -> None:
        self._gpio.output(self._dc, self._gpio.LOW)
        self._spi.writebytes([data])

    def _data(self, data: int) -> None:
        self._gpio.output(self._dc, self._gpio.HIGH)
        self._spi.writebytes([data])

    def _data_bytes(self, payload: bytes) -> None:
        self._gpio.output(self._dc, self._gpio.HIGH)
        chunk = 4096
        for start in range(0, len(payload), chunk):
            self._spi.writebytes(list(payload[start:start + chunk]))

    def _reset(self) -> None:
        for level, pause in ((1, 0.01), (0, 0.01), (1, 0.12)):
            self._gpio.output(self._rst, level)
            time.sleep(pause)

    def _init_display(self) -> None:
        self._reset()
        self._command(0x36); self._data(0x70)          # memory data access control
        self._command(0x3A); self._data(0x05)          # 16-bit/pixel (RGB565)
        self._command(0xB2)                            # porch control
        for value in (0x0C, 0x0C, 0x00, 0x33, 0x33):
            self._data(value)
        self._command(0xB7); self._data(0x35)          # gate control
        self._command(0xBB); self._data(0x19)          # VCOM
        self._command(0xC0); self._data(0x2C)
        self._command(0xC2); self._data(0x01)
        self._command(0xC3); self._data(0x12)          # VRH
        self._command(0xC4); self._data(0x20)          # VDV
        self._command(0xC6); self._data(0x0F)          # frame rate
        self._command(0xD0); self._data(0xA4); self._data(0xA1)
        self._command(0xE0)                            # positive gamma
        for value in (0xD0, 0x04, 0x0D, 0x11, 0x13, 0x2B, 0x3F, 0x54, 0x4C, 0x18, 0x0D, 0x0B, 0x1F, 0x23):
            self._data(value)
        self._command(0xE1)                            # negative gamma
        for value in (0xD0, 0x04, 0x0C, 0x11, 0x13, 0x2C, 0x3F, 0x44, 0x51, 0x2F, 0x1F, 0x1F, 0x20, 0x23):
            self._data(value)
        self._command(0x21)                            # inversion on (IPS)
        self._command(0x11)                            # sleep out
        time.sleep(0.12)
        self._command(0x29)                            # display on

    def _set_window(self, x0: int, y0: int, x1: int, y1: int) -> None:
        self._command(0x2A)
        self._data_bytes(bytes([x0 >> 8, x0 & 0xFF, x1 >> 8, x1 & 0xFF]))
        self._command(0x2B)
        self._data_bytes(bytes([y0 >> 8, y0 & 0xFF, y1 >> 8, y1 & 0xFF]))
        self._command(0x2C)

    # --- public ------------------------------------------------------------

    def display(self, image: Image.Image) -> None:
        """Push a Pillow image (resized to 240x240) to the panel."""
        frame = image.convert("RGB").resize((WIDTH, HEIGHT))
        self._set_window(0, 0, WIDTH - 1, HEIGHT - 1)
        self._data_bytes(_to_rgb565(frame))

    def set_backlight(self, on: bool) -> None:
        self._gpio.output(self._bl, self._gpio.HIGH if on else self._gpio.LOW)

    def close(self) -> None:
        try:
            self._command(0x28)  # display off
            self.set_backlight(False)
        finally:
            try:
                self._spi.close()
            finally:
                self._gpio.cleanup([self._rst, self._dc, self._bl])


def _to_rgb565(image: Image.Image) -> bytes:
    """Convert an RGB image to big-endian RGB565 bytes."""
    try:
        import numpy as np  # noqa: PLC0415 — optional fast path

        arr = np.asarray(image, dtype=np.uint16)
        r, g, b = arr[..., 0], arr[..., 1], arr[..., 2]
        rgb565 = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
        return rgb565.astype(">u2").tobytes()
    except ImportError:
        out = bytearray()
        for r, g, b in image.getdata():
            value = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
            out += bytes([value >> 8, value & 0xFF])
        return bytes(out)
