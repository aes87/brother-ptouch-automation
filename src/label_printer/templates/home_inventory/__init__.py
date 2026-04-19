"""Home-inventory pack — moving boxes, warranties, storage bins. All preset-driven."""

from __future__ import annotations

from pathlib import Path

from label_printer.templates.pack import TemplatePack
from label_printer.templates.preset import load_presets

PACK = TemplatePack(
    name="home_inventory",
    version="0.2.0",
    summary="Home-inventory labels — moving boxes, warranties, storage bins.",
    templates=tuple(load_presets(Path(__file__).parent / "presets.toml")),
)
