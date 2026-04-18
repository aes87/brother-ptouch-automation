"""WAP location — access-point name + room/floor."""

from __future__ import annotations

from PIL import Image

from label_printer.engine.layout import render_two_line_label
from label_printer.tape import TapeWidth
from label_printer.templates.base import Template, TemplateField, TemplateMeta


class WapLocationTemplate(Template):
    meta = TemplateMeta(
        category="networking",
        name="wap_location",
        summary="Wireless access point: name + location.",
        fields=[
            TemplateField("name", "AP name / model.", example="U6-LR"),
            TemplateField("location", "Room, floor, or zone.", example="1F office"),
            TemplateField("icon", "Optional icon.", required=False, example="wifi"),
        ],
        default_tape=TapeWidth.MM_12,
    )

    def render(self, data: dict, tape: TapeWidth) -> Image.Image:
        return render_two_line_label(
            tape, str(data["name"]), str(data["location"]), icon=data.get("icon"),
        )
