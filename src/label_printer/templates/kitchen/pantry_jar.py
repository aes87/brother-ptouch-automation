"""Pantry jar label — bold item name, small purchase + optional expiry."""

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


class PantryJarTemplate(Template):
    meta = TemplateMeta(
        category="kitchen",
        name="pantry_jar",
        summary="Pantry item with purchase date and optional expiry.",
        fields=[
            TemplateField("name", "Item name (e.g. 'AP Flour', 'Brown Rice').",
                          example="AP Flour"),
            TemplateField("purchased", "Purchase date (YYYY-MM-DD).", example="2026-04-19"),
            TemplateField("expires", "Optional expiry date.", required=False,
                          example="2027-04-19"),
        ],
        default_tape=TapeWidth.MM_12,
    )

    def render(self, data: dict, tape: TapeWidth) -> Image.Image:
        name = str(data["name"])
        purchased = str(data["purchased"])
        expires = data.get("expires")

        sub = f"{purchased}" + (f" · exp {expires}" if expires else "")
        layout = TwoLineLayout(tape=tape)

        max_w = mm_to_dots(120)
        name_font = fit_text_to_box(name, max_w, layout.primary_h, DEFAULT_BOLD)
        sub_font = load_font(DEFAULT_FONT, layout.secondary_h - 2)

        length_dots = max(text_width(name, name_font), text_width(sub, sub_font)) + mm_to_dots(6)
        canvas = LabelCanvas.create(tape, length_mm=length_dots * 25.4 / 180)

        draw_row(canvas, name, name_font, layout.primary_y)
        draw_row(canvas, sub, sub_font, layout.secondary_y)
        return canvas.image
