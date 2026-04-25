"""Electronics pack — cable flag (bespoke wrap geometry), component_bin preset, PSU polarity (bespoke)."""

from __future__ import annotations

from pathlib import Path

from label_printer.templates.electronics.cable_flag import CableFlagTemplate
from label_printer.templates.electronics.psu_polarity import PsuPolarityTemplate
from label_printer.templates.pack import TemplatePack
from label_printer.templates.preset import load_presets

PACK = TemplatePack(
    name="electronics",
    version="0.4.0",
    summary="Electronics labels — cable flags, parts bins, PSU polarity.",
    templates=(
        *load_presets(Path(__file__).parent / "presets.toml"),
        CableFlagTemplate(),
        PsuPolarityTemplate(),
    ),
)
