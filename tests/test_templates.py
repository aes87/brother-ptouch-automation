"""Smoke tests: every registered template renders + encodes at 12mm and 24mm."""

from __future__ import annotations

import pytest
from PIL import Image

from label_printer import TapeWidth, encode_job
from label_printer.tape import geometry_for
from label_printer.templates import default_registry

_FIXTURES: dict[str, dict[str, object]] = {
    "kitchen/pantry_jar":      {"name": "FLOUR", "purchased": "2026-04-19", "expires": "2027-04-19"},
    "kitchen/spice":           {"name": "SMOKED PAPRIKA", "origin": "Spain", "best_by": "2027-01"},
    "kitchen/leftover":        {"contents": "chili", "cooked": "2026-04-19", "eat_within_days": 4},
    "kitchen/freezer":         {"contents": "bolognese", "frozen": "2026-04-19", "portion": "2 serves"},
    "electronics/cable_flag":  {"source": "NAS", "dest": "SWITCH p3"},
    "electronics/component_bin": {"value": "10kΩ", "footprint": "0805", "tolerance": "1%"},
    "electronics/psu_polarity": {"voltage": "12V", "current": "2A"},
    "three_d_printing/filament_spool": {
        "material": "PLA", "color": "Obsidian Black", "brand": "Bambu",
        "opened": "2026-04-19", "nozzle_temp": "200-220", "bed_temp": "60",
    },
    "three_d_printing/print_bin": {
        "part": "Fan tub clip v2", "project": "fan-tub-adapter", "qty": "4",
    },
    "three_d_printing/tool_tag": {"tool": "Calipers", "owner": "aes / 3d-printing"},
}


@pytest.fixture(scope="module")
def registry():
    return default_registry()


@pytest.mark.parametrize("qualified,data", list(_FIXTURES.items()))
@pytest.mark.parametrize("tape", [TapeWidth.MM_12, TapeWidth.MM_24])
def test_template_renders_and_encodes(qualified: str, data: dict, tape: TapeWidth, registry):
    template = registry.get(qualified)
    resolved = template.validate(data)
    image = template.render(resolved, tape)

    assert isinstance(image, Image.Image)
    geom = geometry_for(tape)
    assert image.height == geom.print_pins
    assert image.width > 10

    # Encoding round-trip must succeed.
    data_bytes = encode_job(image, tape)
    assert len(data_bytes) > 200
    assert data_bytes.endswith(b"\x1a")


def test_registry_covers_all_fixtures(registry):
    assert set(_FIXTURES) == set(registry.templates)


def test_missing_required_field_raises(registry):
    template = registry.get("kitchen/pantry_jar")
    with pytest.raises(ValueError):
        template.validate({})
