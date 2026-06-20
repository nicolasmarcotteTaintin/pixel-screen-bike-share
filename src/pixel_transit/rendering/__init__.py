"""Rendering layer: turn a provider's view model into a 64x64 image."""

from __future__ import annotations

from PIL import Image

from ..providers.base import BikeShareView, CarShareView, Provider, logo_path
from . import bikeshare, carshare


def render(view: object, provider: Provider) -> Image.Image:
    """Dispatch to the renderer matching the provider's ``kind``."""
    path = logo_path(provider.logo_filename)
    if isinstance(view, BikeShareView):
        return bikeshare.render(view, path, provider.fallback_text)
    if isinstance(view, CarShareView):
        return carshare.render(view, path, provider.fallback_text)
    raise TypeError(f"Unsupported view model: {type(view)!r}")
