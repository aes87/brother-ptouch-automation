"""3D-printing pack — filament spools, print bins, tool tags. All preset-driven."""

from __future__ import annotations

from pathlib import Path

from label_printer.templates.pack import TemplatePack
from label_printer.templates.preset import load_presets

PACK = TemplatePack(
    name="three_d_printing",
    version="0.2.0",
    summary="3D-printing labels — filament spools, print bins, tool tags.",
    templates=tuple(load_presets(Path(__file__).parent / "presets.toml")),
)
