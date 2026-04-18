"""Thermometer calibration — instrument + ice-point / steam-point verification date."""

from __future__ import annotations

from PIL import Image

from label_printer.engine.layout import render_two_line_label
from label_printer.tape import TapeWidth
from label_printer.templates.base import Template, TemplateField, TemplateMeta


class ThermometerCalTemplate(Template):
    meta = TemplateMeta(
        category="calibration",
        name="thermometer_cal",
        summary="Thermometer calibration: instrument + last ice/steam check.",
        fields=[
            TemplateField("instrument", "Thermometer identifier.",
                          example="Thermapen ONE"),
            TemplateField("ice_point_c", "Ice-point reading °C.", example="0.1"),
            TemplateField("checked", "Date of last check.", example="2026-03-28"),
            TemplateField("icon", "Optional icon.", required=False,
                          example="thermometer"),
        ],
        default_tape=TapeWidth.MM_12,
    )

    def render(self, data: dict, tape: TapeWidth) -> Image.Image:
        return render_two_line_label(
            tape,
            f"{data['instrument']} · ice {data['ice_point_c']}°C",
            f"checked {data['checked']}",
            icon=data.get("icon"),
        )
