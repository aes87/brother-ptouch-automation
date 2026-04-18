"""Leftover label — what + when cooked + eat-by."""

from __future__ import annotations

from datetime import date, timedelta

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


class LeftoverTemplate(Template):
    meta = TemplateMeta(
        category="kitchen",
        name="leftover",
        summary="Leftovers: contents + cooked date + auto-computed eat-by.",
        fields=[
            TemplateField("contents", "What's in the container.", example="chili"),
            TemplateField("cooked", "Date cooked (YYYY-MM-DD).", example="2026-04-19"),
            TemplateField("eat_within_days", "Days until eat-by.", required=False, default=4),
        ],
        default_tape=TapeWidth.MM_12,
    )

    def render(self, data: dict, tape: TapeWidth) -> Image.Image:
        contents = str(data["contents"])
        cooked = date.fromisoformat(str(data["cooked"]))
        days = int(data.get("eat_within_days") or 4)
        eat_by = cooked + timedelta(days=days)

        geom = geometry_for(tape)
        sub_h = max(10, int(geom.print_pins * 0.30))
        name_h = geom.print_pins - sub_h - 4

        name = contents.upper()
        name_font = fit_text_to_box(name, mm_to_dots(100), name_h, DEFAULT_BOLD)
        name_w, _ = text_size(name, name_font)

        sub = f"{cooked.isoformat()} → eat by {eat_by.isoformat()}"
        sub_font = load_font(DEFAULT_FONT, sub_h)
        sub_w, _ = text_size(sub, sub_font)

        length_dots = max(name_w, sub_w) + mm_to_dots(6)
        canvas = LabelCanvas.create(tape, length_mm=length_dots * 25.4 / 180)

        draw_centered_text(canvas, name, name_font, y=2)
        draw_centered_text(canvas, sub, sub_font, y=name_h + 4)
        return canvas.image
