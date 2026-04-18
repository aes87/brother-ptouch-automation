"""Shared test helpers."""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image, ImageDraw

GOLDEN_DIR = Path(__file__).parent / "golden"


def make_hello_image(width: int, height: int, text: str = "HELLO") -> Image.Image:
    """Build a deterministic test image (no external fonts)."""
    img = Image.new("1", (width, height), 1)  # white
    draw = ImageDraw.Draw(img)
    draw.text((2, 2), text, fill=0)  # black, default bitmap font
    return img


@pytest.fixture
def golden_dir() -> Path:
    GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
    return GOLDEN_DIR
