"""Utility-pack templates that need extra fixtures (real images)."""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from label_printer import TapeWidth, encode_job
from label_printer.tape import geometry_for
from label_printer.templates import default_registry


@pytest.fixture(scope="module")
def registry():
    return default_registry()


def test_qr_renders_and_encodes(registry):
    template = registry.get("utility/qr")
    data = template.validate({"data": "https://example.com/very/long/url", "caption": "site"})
    img = template.render(data, TapeWidth.MM_12)
    geom = geometry_for(TapeWidth.MM_12)
    assert img.height == geom.print_pins
    cmd = encode_job(img, TapeWidth.MM_12)
    assert cmd.endswith(b"\x1a")


def test_qr_without_caption_is_square(registry):
    template = registry.get("utility/qr")
    img = template.render({"data": "hello"}, TapeWidth.MM_12)
    # Width should be close to height (QR is square) plus a tiny right margin.
    assert abs(img.width - img.height) < 20


def test_image_template_scales_to_tape(tmp_path: Path, registry):
    src = tmp_path / "icon.png"
    Image.new("RGB", (200, 200), "black").save(src)
    template = registry.get("utility/image")
    img = template.render({"path": str(src), "caption": "ICON"}, TapeWidth.MM_12)
    geom = geometry_for(TapeWidth.MM_12)
    assert img.height == geom.print_pins
    cmd = encode_job(img, TapeWidth.MM_12)
    assert cmd.endswith(b"\x1a")
