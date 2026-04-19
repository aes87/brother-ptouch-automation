"""Media pack — bookshelf tags, archive boxes, CDs / records. All preset-driven."""

from __future__ import annotations

from pathlib import Path

from label_printer.templates.pack import TemplatePack
from label_printer.templates.preset import load_presets

PACK = TemplatePack(
    name="media",
    version="0.2.0",
    summary="Media labels — bookshelf tags, archive boxes, CDs/records.",
    templates=tuple(load_presets(Path(__file__).parent / "presets.toml")),
)
