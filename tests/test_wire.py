"""Wire-diameter resolver unit tests."""

from __future__ import annotations

import math

import pytest

from label_printer.engine.wire import (
    UnknownWireError,
    diameter_mm,
    known_awg,
    known_specs,
    wrap_length_mm,
)


@pytest.mark.parametrize("spec,expected", [
    ("ethernet", 5.5),
    ("Cat6", 5.5),
    ("USB-C", 3.5),
    ("hdmi", 7.0),
    ("ac", 8.0),
])
def test_keyword_lookup(spec: str, expected: float):
    assert diameter_mm(spec) == expected


@pytest.mark.parametrize("spec,expected", [
    ("18AWG", 2.6),
    ("18 AWG", 2.6),
    ("18 awg", 2.6),
    ("18 ga", 2.6),
    ("10AWG", 5.5),
    ("24 awg", 1.4),
])
def test_awg_lookup(spec: str, expected: float):
    assert diameter_mm(spec) == expected


@pytest.mark.parametrize("spec,expected", [
    ("5mm", 5.0),
    ("7.5mm", 7.5),
    ("12 mm", 12.0),
])
def test_literal_mm(spec: str, expected: float):
    assert diameter_mm(spec) == expected


def test_numeric_inputs():
    assert diameter_mm(6) == 6.0
    assert diameter_mm(4.5) == 4.5


def test_unknown_raises():
    with pytest.raises(UnknownWireError):
        diameter_mm("teleporter-cable")
    with pytest.raises(UnknownWireError):
        diameter_mm("")


def test_wrap_length():
    # π * 5.5 + 3 ≈ 20.28
    assert wrap_length_mm(5.5) == pytest.approx(math.pi * 5.5 + 3.0)
    assert wrap_length_mm(5.5, overlap_mm=0) == pytest.approx(math.pi * 5.5)


def test_known_listings_are_non_empty():
    assert len(known_specs()) > 30
    assert len(known_awg()) > 5


def test_cable_flag_template_uses_wire_spec():
    from label_printer import TapeWidth
    from label_printer.templates import default_registry
    reg = default_registry()
    tpl = reg.get("electronics/cable_flag")

    thin = tpl.render({"source": "A", "dest": "B", "wire": "24 AWG"}, TapeWidth.MM_12)
    thick = tpl.render({"source": "A", "dest": "B", "wire": "extension-cord"}, TapeWidth.MM_12)
    # Thicker cable needs a longer wrap section → longer overall label.
    assert thick.width > thin.width
