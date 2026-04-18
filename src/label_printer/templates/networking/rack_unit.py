"""Rack unit — U-position + device identifier."""

from __future__ import annotations

from PIL import Image

from label_printer.engine.layout import render_two_line_label
from label_printer.tape import TapeWidth
from label_printer.templates.base import Template, TemplateField, TemplateMeta


class RackUnitTemplate(Template):
    meta = TemplateMeta(
        category="networking",
        name="rack_unit",
        summary="Rack unit label: U-position + device name.",
        fields=[
            TemplateField("unit", "U-position (e.g. 'U14').", example="U14"),
            TemplateField("device", "Device name / model.", example="UDM Pro"),
            TemplateField("icon", "Optional icon.", required=False, example="server"),
        ],
        default_tape=TapeWidth.MM_12,
    )

    def render(self, data: dict, tape: TapeWidth) -> Image.Image:
        return render_two_line_label(
            tape, str(data["unit"]), str(data["device"]), icon=data.get("icon"),
        )
