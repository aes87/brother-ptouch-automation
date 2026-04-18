"""Warranty — item + expiry + optional receipt location."""

from __future__ import annotations

from PIL import Image

from label_printer.engine.layout import render_two_line_label
from label_printer.tape import TapeWidth
from label_printer.templates.base import Template, TemplateField, TemplateMeta


class WarrantyTemplate(Template):
    meta = TemplateMeta(
        category="home_inventory",
        name="warranty",
        summary="Warranty label: item + expiry + optional receipt pointer.",
        fields=[
            TemplateField("item", "Item name.", example="Dishwasher"),
            TemplateField("expires", "Warranty expiry date.", example="2030-09-12"),
            TemplateField("receipt", "Optional receipt pointer.", required=False,
                          example="vault:warranties/dishwasher"),
            TemplateField("icon", "Optional icon.", required=False, example="shield"),
        ],
        default_tape=TapeWidth.MM_12,
    )

    def render(self, data: dict, tape: TapeWidth) -> Image.Image:
        sub = f"warranty exp {data['expires']}"
        if data.get("receipt"):
            sub = f"{sub} · {data['receipt']}"
        return render_two_line_label(
            tape, str(data["item"]), sub, icon=data.get("icon"),
        )
