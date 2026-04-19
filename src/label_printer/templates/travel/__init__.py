"""Travel pack — luggage tags, gear bags, power banks. All preset-driven."""

from __future__ import annotations

from pathlib import Path

from label_printer.templates.pack import TemplatePack
from label_printer.templates.preset import load_presets

PACK = TemplatePack(
    name="travel",
    version="0.2.0",
    summary="Travel labels — luggage tags, gear bags, power banks.",
    templates=tuple(load_presets(Path(__file__).parent / "presets.toml")),
)
