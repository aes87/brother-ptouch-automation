"""Tests for the post-render compose decorator."""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from label_printer import TapeWidth
from label_printer.engine.compose import compose_extras, strip_template_handled
from label_printer.tape import geometry_for
from label_printer.templates import default_registry


@pytest.fixture(scope="module")
def registry():
    return default_registry()


def _render_body(qualified: str, data: dict, tape: TapeWidth, registry) -> Image.Image:
    template = registry.get(qualified)
    return template.render(template.validate(data), tape)


def test_link_appends_qr_on_the_right(registry):
    tape = TapeWidth.MM_12
    body = _render_body("kitchen/pantry_jar",
                        {"name": "FLOUR", "purchased": "2026-04-17"}, tape, registry)
    composed = compose_extras(body, {"link": "vault:kitchen/flour"}, tape)

    # QR is sized to print height, so composed image is wider by at least that much.
    geom = geometry_for(tape)
    assert composed.height == body.height == geom.print_pins
    assert composed.width > body.width + geom.print_pins // 2


def test_image_appends_bitmap_on_the_right(tmp_path: Path, registry):
    tape = TapeWidth.MM_12

    # Create a small bitmap to attach.
    icon = Image.new("RGB", (40, 40), "black")
    icon_path = tmp_path / "icon.png"
    icon.save(icon_path)

    body = _render_body("kitchen/pantry_jar",
                        {"name": "FLOUR", "purchased": "2026-04-17"}, tape, registry)
    composed = compose_extras(body, {"image": str(icon_path)}, tape)

    assert composed.height == body.height
    assert composed.width > body.width


def test_no_extras_returns_body_unchanged(registry):
    tape = TapeWidth.MM_12
    body = _render_body("kitchen/pantry_jar",
                        {"name": "FLOUR", "purchased": "2026-04-17"}, tape, registry)
    composed = compose_extras(body, {}, tape)
    assert composed is body


def test_strip_template_handled_removes_template_owned_keys(registry):
    qr_template = registry.get("utility/qr")
    extras = {"link": "anything", "image": "/tmp/unused.png"}
    stripped = strip_template_handled(extras, qr_template)
    assert "link" not in stripped  # utility/qr handles link internally
    assert stripped["image"] == "/tmp/unused.png"


def test_strip_passes_through_for_plain_template(registry):
    plain = registry.get("kitchen/pantry_jar")
    extras = {"link": "vault:x", "image": "/tmp/y.png"}
    assert strip_template_handled(extras, plain) == extras


@pytest.mark.parametrize(
    "qualified,data",
    [
        ("kitchen/spice", {"name": "Paprika", "origin": "Spain", "best_by": "2027-01"}),
        ("three_d_printing/filament_spool", {
            "material": "PLA", "color": "Black", "brand": "Bambu", "opened": "2026-04-01",
        }),
        ("electronics/component_bin", {"value": "10k", "footprint": "0805"}),
        ("pet/collar_backup", {"name": "Rex", "contact": "+1 555 0100"}),
    ],
)
def test_link_works_across_template_packs(qualified: str, data: dict, registry):
    tape = TapeWidth.MM_12
    body = _render_body(qualified, data, tape, registry)
    composed = compose_extras(body, {"link": f"vault:test/{qualified}"}, tape)
    assert composed.width > body.width
    assert composed.height == body.height
