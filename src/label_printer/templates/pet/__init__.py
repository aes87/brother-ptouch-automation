"""Pet pack — collar backups, medication schedules, food bowls. All preset-driven."""

from __future__ import annotations

from pathlib import Path

from label_printer.templates.pack import TemplatePack
from label_printer.templates.preset import load_presets

PACK = TemplatePack(
    name="pet",
    version="0.2.0",
    summary="Pet labels — collar backups, medication schedules, food bowls.",
    templates=tuple(load_presets(Path(__file__).parent / "presets.toml")),
)
