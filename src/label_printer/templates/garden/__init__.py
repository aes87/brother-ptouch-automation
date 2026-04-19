"""Garden pack — seed packets, plant tags, row markers. All preset-driven."""

from __future__ import annotations

from pathlib import Path

from label_printer.templates.pack import TemplatePack
from label_printer.templates.preset import load_presets

PACK = TemplatePack(
    name="garden",
    version="0.2.0",
    summary="Garden labels — seed packets, plant tags, row markers.",
    templates=tuple(load_presets(Path(__file__).parent / "presets.toml")),
)
