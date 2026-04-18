"""Freezer label — contents + frozen date + optional portion."""

from __future__ import annotations

from PIL import Image

from label_printer.engine.layout import (
    DEFAULT_BOLD,
    DEFAULT_FONT,
    LabelCanvas,
    TwoLineLayout,
    draw_row,
    fit_text_to_box,
    load_font,
    mm_to_dots,
    text_width,
)
from label_printer.tape import TapeWidth
from label_printer.templates.base import Template, TemplateField, TemplateMeta


class FreezerTemplate(Template):
    meta = TemplateMeta(
        category="kitchen",
        name="freezer",
        summary="Freezer label: contents + frozen date + optional portion size.",
        fields=[
            TemplateField("contents", "What's in the package.", example="Bolognese"),
            TemplateField("frozen", "Date frozen.", example="2026-04-19"),
            TemplateField("portion", "Portion descriptor.", required=False, example="2 serves"),
        ],
        default_tape=TapeWidth.MM_12,
    )

    def render(self, data: dict, tape: TapeWidth) -> Image.Image:
        contents = str(data["contents"])
        frozen = str(data["frozen"])
        portion = data.get("portion")

        sub = f"frozen {frozen}" + (f" · {portion}" if portion else "")
        layout = TwoLineLayout(tape=tape)

        name_font = fit_text_to_box(contents, mm_to_dots(100), layout.primary_h, DEFAULT_BOLD)
        sub_font = load_font(DEFAULT_FONT, layout.secondary_h - 2)
        length = max(text_width(contents, name_font), text_width(sub, sub_font)) + mm_to_dots(6)
        canvas = LabelCanvas.create(tape, length_mm=length * 25.4 / 180)

        draw_row(canvas, contents, name_font, layout.primary_y)
        draw_row(canvas, sub, sub_font, layout.secondary_y)
        return canvas.image
