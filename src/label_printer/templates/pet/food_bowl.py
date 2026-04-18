"""Pet food bowl — pet + food + portion."""

from __future__ import annotations

from PIL import Image

from label_printer.engine.layout import render_two_line_label
from label_printer.tape import TapeWidth
from label_printer.templates.base import Template, TemplateField, TemplateMeta


class FoodBowlTemplate(Template):
    meta = TemplateMeta(
        category="pet",
        name="food_bowl",
        summary="Feeding bowl / container: pet + food + portion.",
        fields=[
            TemplateField("pet", "Pet name.", example="Rex"),
            TemplateField("food", "Food identifier.", example="Acana Adult"),
            TemplateField("portion", "Portion / amount.", example="1 cup"),
            TemplateField("icon", "Optional icon.", required=False, example="paw-print"),
        ],
        default_tape=TapeWidth.MM_12,
    )

    def render(self, data: dict, tape: TapeWidth) -> Image.Image:
        return render_two_line_label(
            tape,
            f"{data['pet']} · {data['food']}",
            str(data["portion"]),
            icon=data.get("icon"),
        )
