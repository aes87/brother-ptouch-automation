"""Leftover label — contents + cooked date + auto-computed eat-by."""

from __future__ import annotations

from datetime import date, timedelta

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


class LeftoverTemplate(Template):
    meta = TemplateMeta(
        category="kitchen",
        name="leftover",
        summary="Leftovers: contents + cooked date + auto-computed eat-by.",
        fields=[
            TemplateField("contents", "What's in the container.", example="Chili"),
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

        sub = f"{cooked.isoformat()} → eat by {eat_by.isoformat()}"
        layout = TwoLineLayout(tape=tape)

        name_font = fit_text_to_box(contents, mm_to_dots(100), layout.primary_h, DEFAULT_BOLD)
        sub_font = load_font(DEFAULT_FONT, layout.secondary_h - 2)
        length = max(text_width(contents, name_font), text_width(sub, sub_font)) + mm_to_dots(6)
        canvas = LabelCanvas.create(tape, length_mm=length * 25.4 / 180)

        draw_row(canvas, contents, name_font, layout.primary_y)
        draw_row(canvas, sub, sub_font, layout.secondary_y)
        return canvas.image
