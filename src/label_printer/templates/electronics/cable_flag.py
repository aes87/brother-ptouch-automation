"""Cable flag — fold-over label with source → destination on both halves."""

from __future__ import annotations

from PIL import Image

from label_printer.engine.layout import (
    DEFAULT_BOLD,
    LabelCanvas,
    draw_dashed_vline,
    fit_text_to_box,
    mm_to_dots,
    text_size,
)
from label_printer.tape import TapeWidth, geometry_for
from label_printer.templates.base import Template, TemplateField, TemplateMeta


class CableFlagTemplate(Template):
    meta = TemplateMeta(
        category="electronics",
        name="cable_flag",
        summary="Cable flag: 'source → dest' printed twice around a fold line.",
        fields=[
            TemplateField("source", "Source end.", example="NAS"),
            TemplateField("dest", "Destination end.", example="SWITCH p3"),
        ],
        default_tape=TapeWidth.MM_12,
    )

    def render(self, data: dict, tape: TapeWidth) -> Image.Image:
        src = str(data["source"])
        dst = str(data["dest"])
        text = f"{src} → {dst}"

        geom = geometry_for(tape)
        half_w = mm_to_dots(32)  # per half
        font = fit_text_to_box(text, half_w - mm_to_dots(2), geom.print_pins - 4, DEFAULT_BOLD)
        w, h = text_size(text, font)

        half_len = max(w + mm_to_dots(4), half_w)
        total_len = half_len * 2

        canvas = LabelCanvas.create(tape, length_mm=total_len * 25.4 / 180)
        y = (geom.print_pins - h) // 2

        # Left half
        canvas.draw.text(((half_len - w) // 2, y), text, fill="black", font=font)
        # Right half (same text, same orientation — reads correctly once folded)
        canvas.draw.text((half_len + (half_len - w) // 2, y), text, fill="black", font=font)
        # Fold line in the middle
        draw_dashed_vline(canvas, half_len)
        return canvas.image
