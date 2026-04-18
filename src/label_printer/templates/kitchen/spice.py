"""Spice rack label — name + optional origin/best-by."""

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


class SpiceTemplate(Template):
    meta = TemplateMeta(
        category="kitchen",
        name="spice",
        summary="Spice label: name + optional origin + best-by.",
        fields=[
            TemplateField("name", "Spice name.", example="SMOKED PAPRIKA"),
            TemplateField("origin", "Origin / variety.", required=False, example="Spain"),
            TemplateField("best_by", "Best-by date.", required=False, example="2027-01"),
        ],
        default_tape=TapeWidth.MM_12,
    )

    def render(self, data: dict, tape: TapeWidth) -> Image.Image:
        name = str(data["name"]).upper()
        origin = data.get("origin")
        best_by = data.get("best_by")

        geom = geometry_for(tape)
        sub_h = max(10, int(geom.print_pins * 0.30)) if (origin or best_by) else 0
        name_h = geom.print_pins - (sub_h + 4 if sub_h else 0)

        name_font = fit_text_to_box(name, mm_to_dots(100), name_h, DEFAULT_BOLD)
        name_w, _ = text_size(name, name_font)

        sub = " · ".join(s for s in [origin, (f"bb {best_by}" if best_by else None)] if s)
        sub_w = 0
        if sub:
            sub_font = load_font(DEFAULT_FONT, sub_h)
            sub_w, _ = text_size(sub, sub_font)

        length_dots = max(name_w, sub_w) + mm_to_dots(6)
        canvas = LabelCanvas.create(tape, length_mm=length_dots * 25.4 / 180)

        if sub:
            draw_centered_text(canvas, name, name_font, y=2)
            draw_centered_text(canvas, sub, sub_font, y=name_h + 4)
        else:
            draw_centered_text(canvas, name, name_font)
        return canvas.image
