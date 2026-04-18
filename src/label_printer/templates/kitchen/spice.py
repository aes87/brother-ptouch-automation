"""Spice rack label — name + optional origin / best-by."""

from __future__ import annotations

from PIL import Image

from label_printer.engine.layout import (
    DEFAULT_BOLD,
    DEFAULT_FONT,
    LabelCanvas,
    TwoLineLayout,
    draw_row,
    fit_text_to_box,
    fit_text_to_height,
    load_font,
    mm_to_dots,
    text_width,
)
from label_printer.tape import TapeWidth, geometry_for
from label_printer.templates.base import Template, TemplateField, TemplateMeta


class SpiceTemplate(Template):
    meta = TemplateMeta(
        category="kitchen",
        name="spice",
        summary="Spice label: name + optional origin + best-by.",
        fields=[
            TemplateField("name", "Spice name.", example="Smoked Paprika"),
            TemplateField("origin", "Origin / variety.", required=False, example="Spain"),
            TemplateField("best_by", "Best-by date.", required=False, example="2027-01"),
        ],
        default_tape=TapeWidth.MM_12,
    )

    def render(self, data: dict, tape: TapeWidth) -> Image.Image:
        name = str(data["name"])
        origin = data.get("origin")
        best_by = data.get("best_by")
        sub_parts = [s for s in [origin, (f"bb {best_by}" if best_by else None)] if s]
        sub = " · ".join(sub_parts)

        max_w = mm_to_dots(100)
        if sub:
            layout = TwoLineLayout(tape=tape)
            name_font = fit_text_to_box(name, max_w, layout.primary_h, DEFAULT_BOLD)
            sub_font = load_font(DEFAULT_FONT, layout.secondary_h - 2)
            length = max(text_width(name, name_font), text_width(sub, sub_font)) + mm_to_dots(6)
            canvas = LabelCanvas.create(tape, length_mm=length * 25.4 / 180)
            draw_row(canvas, name, name_font, layout.primary_y)
            draw_row(canvas, sub, sub_font, layout.secondary_y)
        else:
            geom = geometry_for(tape)
            avail = geom.print_pins - 4
            name_font = fit_text_to_height(name, avail, DEFAULT_BOLD)
            length = text_width(name, name_font) + mm_to_dots(6)
            canvas = LabelCanvas.create(tape, length_mm=length * 25.4 / 180)
            draw_row(canvas, name, name_font, 2)
        return canvas.image
