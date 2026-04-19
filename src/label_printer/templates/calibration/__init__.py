"""Calibration pack — instrument cal stickers, certificate IDs, thermometer checks. All preset-driven."""

from __future__ import annotations

from pathlib import Path

from label_printer.templates.pack import TemplatePack
from label_printer.templates.preset import load_presets

PACK = TemplatePack(
    name="calibration",
    version="0.2.0",
    summary="Calibration labels — instrument cal, cert IDs, thermometer checks.",
    templates=tuple(load_presets(Path(__file__).parent / "presets.toml")),
)
