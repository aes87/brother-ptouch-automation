"""Pet medication schedule — pet + med + dose."""

from __future__ import annotations

from PIL import Image

from label_printer.engine.layout import render_two_line_label
from label_printer.tape import TapeWidth
from label_printer.templates.base import Template, TemplateField, TemplateMeta


class MedScheduleTemplate(Template):
    meta = TemplateMeta(
        category="pet",
        name="med_schedule",
        summary="Pet medication schedule: pet + med + dose + cadence.",
        fields=[
            TemplateField("pet", "Pet name.", example="Rex"),
            TemplateField("med", "Medication.", example="Apoquel 16mg"),
            TemplateField("cadence", "How often.", example="1× daily"),
            TemplateField("icon", "Optional icon.", required=False, example="pill"),
        ],
        default_tape=TapeWidth.MM_12,
    )

    def render(self, data: dict, tape: TapeWidth) -> Image.Image:
        return render_two_line_label(
            tape,
            f"{data['pet']} · {data['med']}",
            str(data["cadence"]),
            icon=data.get("icon"),
        )
