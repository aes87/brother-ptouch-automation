"""Plant tag — name + date planted + optional icon."""

from __future__ import annotations

from PIL import Image

from label_printer.engine.layout import render_two_line_label
from label_printer.tape import TapeWidth
from label_printer.templates.base import Template, TemplateField, TemplateMeta


class PlantTagTemplate(Template):
    meta = TemplateMeta(
        category="garden",
        name="plant_tag",
        summary="Plant tag for a pot or seed tray.",
        fields=[
            TemplateField("name", "Plant name.", example="Basil"),
            TemplateField("planted", "Date planted or transplanted.",
                          example="2026-04-15"),
            TemplateField("icon", "Optional icon (e.g. 'leaf').", required=False,
                          example="leaf"),
        ],
        default_tape=TapeWidth.MM_12,
    )

    def render(self, data: dict, tape: TapeWidth) -> Image.Image:
        return render_two_line_label(
            tape,
            str(data["name"]),
            f"planted {data['planted']}",
            icon=data.get("icon"),
        )
