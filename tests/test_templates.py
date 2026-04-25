"""Smoke tests: every registered template renders + encodes at 12mm and 24mm."""

from __future__ import annotations

import pytest
from PIL import Image

from label_printer import TapeWidth, encode_job
from label_printer.tape import geometry_for
from label_printer.templates import default_registry

_FIXTURES: dict[str, dict[str, object]] = {
    "kitchen/pantry_jar":      {"name": "AP Flour", "purchased": "2026-04-19", "expires": "2027-04-19"},
    "kitchen/spice":           {"name": "Smoked Paprika", "origin": "Spain", "best_by": "2027-01"},
    "kitchen/leftover":        {"contents": "Chili", "cooked": "2026-04-19", "eat_within_days": 4},
    "kitchen/freezer":         {"contents": "Bolognese", "frozen": "2026-04-19", "portion": "2 serves"},
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
    "utility/qr": {"data": "https://github.com/aes87/brother-ptouch-automation", "caption": "repo"},
    "garden/seed_packet": {"variety": "Brandywine tomato", "sow_by": "2026-05-15", "year": "2025"},
    "garden/plant_tag": {"name": "Basil", "planted": "2026-04-15"},
    "garden/row_marker": {"crop": "Tomato", "variety": "Cherokee Purple"},
    "networking/patch_port": {"port": "P12", "vlan": "VLAN 20", "dest": "sw1 g0/3"},
    "networking/rack_unit": {"unit": "U14", "device": "UDM Pro"},
    "networking/wap_location": {"name": "U6-LR", "location": "1F office"},
    "workshop/hazard": {"hazard": "flammable", "text": "ACETONE", "code": "GHS02"},
    "workshop/tool_id": {"name": "Cordless drill", "owner": "aes / garage", "project": "Makita"},
    "workshop/torque_cal": {"tool": "CDI 1/2\"", "range_nm": "20-100", "last_cal": "2026-03-10"},
    "workshop/first_aid": {"kit": "Garage kit #2", "expires": "2027-08"},
    "home_inventory/moving_box": {"room": "Kitchen", "contents": "pots, boards", "fragile": "yes"},
    "home_inventory/warranty": {"item": "Dishwasher", "expires": "2030-09-12"},
    "home_inventory/storage_bin": {"location": "Basement bay 3", "contents": "Holiday lights"},
    "media/bookshelf_tag": {"title": "Refactoring", "author": "Fowler", "callno": "QA76.F69"},
    "media/archive_box": {"label": "2024 taxes", "retain_until": "2031-04-15"},
    "media/cd_record": {"title": "Kind of Blue", "artist": "Miles Davis", "year": "1959"},
    "pet/collar_backup": {"name": "Rex", "contact": "+1 555 0100"},
    "pet/med_schedule": {"pet": "Rex", "med": "Apoquel 16mg", "cadence": "1x daily"},
    "pet/food_bowl": {"pet": "Rex", "food": "Acana Adult", "portion": "1 cup"},
    "travel/luggage_tag": {"name": "aes87", "contact": "aesthe@example.com"},
    "travel/gear_bag": {"bag": "Peak Design 30L", "purpose": "Banff 2026"},
    "travel/power_bank": {"capacity_mah": "20000", "charged": "2026-04-15", "model": "Anker 737"},
    "calibration/instrument_cal": {"instrument": "Fluke 87V", "next_due": "2027-05-01", "owner": "QA lab"},
    "calibration/cert_id": {"cert_no": "CAL-2026-00421", "issuer": "ISO/IEC 17025"},
    "calibration/thermometer_cal": {"instrument": "Thermapen ONE", "ice_point_c": "0.1", "checked": "2026-03-28"},
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
    # Every fixture must exist in the registry. The reverse isn't required:
    # some templates (e.g. utility/image) need external resources that don't
    # belong in a unit-test fixture.
    assert set(_FIXTURES).issubset(set(registry.templates))


def test_missing_required_field_raises(registry):
    template = registry.get("kitchen/pantry_jar")
    with pytest.raises(ValueError):
        template.validate({})


@pytest.mark.parametrize("tape", [TapeWidth.MM_12, TapeWidth.MM_24])
def test_cable_flag_with_title_date_details_and_link(tape: TapeWidth, registry):
    """The merged cable_flag accepts title + date + multi-line details + per-face QR."""
    template = registry.get("electronics/cable_flag")
    data = template.validate({
        "title": "NAS → SW p3",
        "date": "2026-04-19",
        "details": "VLAN 20\npatch A-14",
        "link": "vault:networking/nas-eth0",
    })
    image = template.render(data, tape)
    assert image.height == geometry_for(tape).print_pins
    assert image.width > 200  # two faces + wrap, well above the 20mm-min floor


def test_cable_flag_requires_title_or_source_dest_pair(registry):
    template = registry.get("electronics/cable_flag")
    with pytest.raises(ValueError):
        template.validate({"date": "2026-04-19"})  # neither title nor source+dest
    with pytest.raises(ValueError):
        template.validate({"source": "NAS"})  # source without dest


def test_cable_flag_handles_extras_internally(registry):
    """compose_extras must skip 'link' and 'image' for cable_flag — it draws them per-face."""
    template = registry.get("electronics/cable_flag")
    assert template.handles_extras == frozenset({"link", "image"})
