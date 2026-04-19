"""Workshop pack — hazard (bespoke GHS), tool_id / torque_cal / first_aid presets."""

from __future__ import annotations

from pathlib import Path

from label_printer.templates.pack import TemplatePack
from label_printer.templates.preset import load_presets
from label_printer.templates.workshop.hazard import HazardTemplate

PACK = TemplatePack(
    name="workshop",
    version="0.2.0",
    summary="Workshop labels — hazards, tool IDs, torque calibration, first-aid.",
    templates=(
        HazardTemplate(),
        *load_presets(Path(__file__).parent / "presets.toml"),
    ),
)
