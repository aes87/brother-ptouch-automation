"""Workshop pack — hazard labels, tool IDs, calibration, first-aid."""

from __future__ import annotations

from label_printer.templates.pack import TemplatePack
from label_printer.templates.workshop.first_aid import FirstAidTemplate
from label_printer.templates.workshop.hazard import HazardTemplate
from label_printer.templates.workshop.tool_id import ToolIdTemplate
from label_printer.templates.workshop.torque_cal import TorqueCalTemplate

PACK = TemplatePack(
    name="workshop",
    version="0.1.0",
    summary="Workshop labels — hazards, tool IDs, torque calibration, first-aid.",
    templates=(
        HazardTemplate(),
        ToolIdTemplate(),
        TorqueCalTemplate(),
        FirstAidTemplate(),
    ),
)
