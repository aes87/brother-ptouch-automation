"""Power-bank label — capacity + last-charged date."""

from __future__ import annotations

from PIL import Image

from label_printer.engine.layout import render_two_line_label
from label_printer.tape import TapeWidth
from label_printer.templates.base import Template, TemplateField, TemplateMeta


class PowerBankTemplate(Template):
    meta = TemplateMeta(
        category="travel",
        name="power_bank",
        summary="Power bank: capacity + last-charged date.",
        fields=[
            TemplateField("capacity_mah", "Capacity in mAh.", example="20000"),
            TemplateField("charged", "Last charged date.", example="2026-04-15"),
            TemplateField("model", "Optional model name.", required=False,
                          example="Anker 737"),
            TemplateField("icon", "Optional icon.", required=False, example="battery"),
        ],
        default_tape=TapeWidth.MM_12,
    )

    def render(self, data: dict, tape: TapeWidth) -> Image.Image:
        primary = f"{data['capacity_mah']} mAh"
        if data.get("model"):
            primary = f"{data['model']} · {primary}"
        return render_two_line_label(
            tape, primary, f"charged {data['charged']}",
            icon=data.get("icon"),
        )
