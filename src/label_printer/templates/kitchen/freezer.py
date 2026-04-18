"""Freezer label — contents + frozen date + portion size."""

from __future__ import annotations

from PIL import Image

from label_printer.engine.layout import (
    DEFAULT_BOLD,
    DEFAULT_FONT,
    LabelCanvas,
    draw_centered_text,
    fit_text_to_box,
    load_font,
    mm_to_dots,
    text_size,
)
from label_printer.tape import TapeWidth, geometry_for
from label_printer.templates.base import Template, TemplateField, TemplateMeta


class FreezerTemplate(Template):
    meta = TemplateMeta(
        category="kitchen",
        name="freezer",
        summary="Freezer label: contents + frozen date + portion size.",
        fields=[
            TemplateField("contents", "What's in the package.", example="Bolognese"),
            TemplateField("frozen", "Date frozen.", example="2026-04-19"),
            TemplateField("portion", "Portion descriptor.", required=False,
                          example="2 serves"),
        ],
        default_tape=TapeWidth.MM_12,
    )

    def render(self, data: dict, tape: TapeWidth) -> Image.Image:
        contents = str(data["contents"]).upper()
        frozen = str(data["frozen"])
        portion = data.get("portion")

        geom = geometry_for(tape)
        sub_h = max(10, int(geom.print_pins * 0.30))
        name_h = geom.print_pins - sub_h - 4

        name_font = fit_text_to_box(contents, mm_to_dots(100), name_h, DEFAULT_BOLD)
        name_w, _ = text_size(contents, name_font)

        sub = f"FROZEN {frozen}" + (f" · {portion}" if portion else "")
        sub_font = load_font(DEFAULT_FONT, sub_h)
        sub_w, _ = text_size(sub, sub_font)

        length_dots = max(name_w, sub_w) + mm_to_dots(6)
        canvas = LabelCanvas.create(tape, length_mm=length_dots * 25.4 / 180)

        draw_centered_text(canvas, contents, name_font, y=2)
        draw_centered_text(canvas, sub, sub_font, y=name_h + 4)
        return canvas.image
