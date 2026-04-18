"""Seed packet — variety + sow-by + optional year."""

from __future__ import annotations

from PIL import Image

from label_printer.engine.layout import render_two_line_label
from label_printer.tape import TapeWidth
from label_printer.templates.base import Template, TemplateField, TemplateMeta


class SeedPacketTemplate(Template):
    meta = TemplateMeta(
        category="garden",
        name="seed_packet",
        summary="Seed packet: variety + sow-by date + optional year.",
        fields=[
            TemplateField("variety", "Cultivar or variety.", example="Brandywine tomato"),
            TemplateField("sow_by", "Sow-by date.", example="2026-05-15"),
            TemplateField("year", "Harvest year.", required=False, example="2025"),
            TemplateField("icon", "Optional icon (e.g. 'sprout').", required=False,
                          example="sprout"),
        ],
        default_tape=TapeWidth.MM_12,
    )

    def render(self, data: dict, tape: TapeWidth) -> Image.Image:
        variety = str(data["variety"])
        sub = f"sow by {data['sow_by']}"
        if data.get("year"):
            sub = f"{data['year']} · {sub}"
        return render_two_line_label(tape, variety, sub, icon=data.get("icon"))
