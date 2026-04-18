"""Instrument calibration — instrument + next-due date."""

from __future__ import annotations

from PIL import Image

from label_printer.engine.layout import render_two_line_label
from label_printer.tape import TapeWidth
from label_printer.templates.base import Template, TemplateField, TemplateMeta


class InstrumentCalTemplate(Template):
    meta = TemplateMeta(
        category="calibration",
        name="instrument_cal",
        summary="Instrument calibration: instrument + next-due date + owner.",
        fields=[
            TemplateField("instrument", "Instrument name.", example="Fluke 87V"),
            TemplateField("next_due", "Next calibration due.", example="2027-05-01"),
            TemplateField("owner", "Optional owner / lab.", required=False,
                          example="QA lab"),
            TemplateField("icon", "Optional icon.", required=False, example="gauge"),
        ],
        default_tape=TapeWidth.MM_12,
    )

    def render(self, data: dict, tape: TapeWidth) -> Image.Image:
        sub = f"next {data['next_due']}"
        if data.get("owner"):
            sub = f"{data['owner']} · {sub}"
        return render_two_line_label(
            tape, str(data["instrument"]), sub, icon=data.get("icon"),
        )
