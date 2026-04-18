"""Garden row marker — crop + variety."""

from __future__ import annotations

from PIL import Image

from label_printer.engine.layout import render_two_line_label
from label_printer.tape import TapeWidth
from label_printer.templates.base import Template, TemplateField, TemplateMeta


class RowMarkerTemplate(Template):
    meta = TemplateMeta(
        category="garden",
        name="row_marker",
        summary="Row marker: crop + variety for outdoor beds.",
        fields=[
            TemplateField("crop", "Crop name.", example="Tomato"),
            TemplateField("variety", "Variety / cultivar.", example="Cherokee Purple"),
            TemplateField("icon", "Optional icon.", required=False, example="carrot"),
        ],
        default_tape=TapeWidth.MM_12,
    )

    def render(self, data: dict, tape: TapeWidth) -> Image.Image:
        return render_two_line_label(
            tape, str(data["crop"]), str(data["variety"]), icon=data.get("icon")
        )
