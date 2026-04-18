"""Gear bag — bag name + purpose / contents."""

from __future__ import annotations

from PIL import Image

from label_printer.engine.layout import render_two_line_label
from label_printer.tape import TapeWidth
from label_printer.templates.base import Template, TemplateField, TemplateMeta


class GearBagTemplate(Template):
    meta = TemplateMeta(
        category="travel",
        name="gear_bag",
        summary="Gear bag: bag identifier + purpose / trip.",
        fields=[
            TemplateField("bag", "Bag identifier.", example="Peak Design 30L"),
            TemplateField("purpose", "Trip / use-case.", example="Banff 2026"),
            TemplateField("icon", "Optional icon.", required=False, example="briefcase"),
        ],
        default_tape=TapeWidth.MM_12,
    )

    def render(self, data: dict, tape: TapeWidth) -> Image.Image:
        return render_two_line_label(
            tape, str(data["bag"]), str(data["purpose"]),
            icon=data.get("icon"),
        )
