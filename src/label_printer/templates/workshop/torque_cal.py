"""Torque wrench calibration — tool + torque range + last calibration date."""

from __future__ import annotations

from PIL import Image

from label_printer.engine.layout import render_two_line_label
from label_printer.tape import TapeWidth
from label_printer.templates.base import Template, TemplateField, TemplateMeta


class TorqueCalTemplate(Template):
    meta = TemplateMeta(
        category="workshop",
        name="torque_cal",
        summary="Torque wrench calibration: tool + range + last-cal date.",
        fields=[
            TemplateField("tool", "Tool name.", example="CDI 1/2\""),
            TemplateField("range_nm", "Torque range, N·m.", example="20-100"),
            TemplateField("last_cal", "Date of last calibration (YYYY-MM-DD).",
                          example="2026-03-10"),
            TemplateField("icon", "Optional icon.", required=False, example="gauge"),
        ],
        default_tape=TapeWidth.MM_12,
    )

    def render(self, data: dict, tape: TapeWidth) -> Image.Image:
        return render_two_line_label(
            tape,
            f"{data['tool']} · {data['range_nm']} N·m",
            f"cal {data['last_cal']}",
            icon=data.get("icon"),
        )
