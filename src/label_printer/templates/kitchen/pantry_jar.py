"""Pantry jar label — large item name, small purchase + expiry dates."""

from __future__ import annotations

from PIL import Image

from label_printer.engine.layout import (
    DEFAULT_BOLD,
    LabelCanvas,
    draw_centered_text,
    fit_text_to_box,
    load_font,
    mm_to_dots,
    text_size,
)
from label_printer.tape import TapeWidth, geometry_for
from label_printer.templates.base import Template, TemplateField, TemplateMeta


class PantryJarTemplate(Template):
    meta = TemplateMeta(
        category="kitchen",
        name="pantry_jar",
        summary="Pantry item with purchase and optional expiry date.",
        fields=[
            TemplateField("name", "Item name (e.g. 'FLOUR', 'BROWN RICE').", example="FLOUR"),
            TemplateField("purchased", "Purchase date (YYYY-MM-DD).", example="2026-04-19"),
            TemplateField("expires", "Optional expiry date.", required=False,
                          example="2027-04-19"),
        ],
        default_tape=TapeWidth.MM_12,
    )

    def render(self, data: dict, tape: TapeWidth) -> Image.Image:
        name = str(data["name"]).upper()
        purchased = str(data["purchased"])
        expires = data.get("expires")

        geom = geometry_for(tape)
        sub_h = max(10, int(geom.print_pins * 0.28))
        name_h = geom.print_pins - sub_h - 4

        # Size the label length to fit the name at the chosen height
        name_font = fit_text_to_box(name, mm_to_dots(120), name_h, DEFAULT_BOLD)
        name_w, _ = text_size(name, name_font)
        sub_font = load_font(DEFAULT_BOLD, sub_h)
        sub = f"{purchased}" + (f" · exp {expires}" if expires else "")
        sub_w, _ = text_size(sub, sub_font)

        length_dots = max(name_w, sub_w) + mm_to_dots(6)
        canvas = LabelCanvas.create(tape, length_mm=length_dots * 25.4 / 180)

        draw_centered_text(canvas, name, name_font, y=2)
        draw_centered_text(canvas, sub, sub_font, y=name_h + 4)
        return canvas.image
