"""First-aid kit — contents summary + expiry."""

from __future__ import annotations

from PIL import Image

from label_printer.engine.layout import render_two_line_label
from label_printer.tape import TapeWidth
from label_printer.templates.base import Template, TemplateField, TemplateMeta


class FirstAidTemplate(Template):
    meta = TemplateMeta(
        category="workshop",
        name="first_aid",
        summary="First-aid kit: contents identifier + expiry / refill date.",
        fields=[
            TemplateField("kit", "Kit identifier.", example="Garage kit #2"),
            TemplateField("expires", "Earliest-expiring item.", example="2027-08"),
            TemplateField("icon", "Optional icon.", required=False, example="shield"),
        ],
        default_tape=TapeWidth.MM_12,
    )

    def render(self, data: dict, tape: TapeWidth) -> Image.Image:
        return render_two_line_label(
            tape,
            str(data["kit"]),
            f"check by {data['expires']}",
            icon=data.get("icon"),
        )
