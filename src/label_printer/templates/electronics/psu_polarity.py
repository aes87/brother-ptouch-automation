"""PSU polarity — voltage / current / polarity icon."""

from __future__ import annotations

from PIL import Image, ImageDraw

from label_printer.engine.layout import (
    DEFAULT_BOLD,
    LabelCanvas,
    fit_text_to_box,
    mm_to_dots,
    text_size,
)
from label_printer.tape import TapeWidth, geometry_for
from label_printer.templates.base import Template, TemplateField, TemplateMeta


def _draw_center_positive_icon(draw: ImageDraw.ImageDraw, x: int, y: int, size: int) -> None:
    """Simple IEC 60417-5926 'centre positive' pictogram."""
    r_outer = size // 2
    cx, cy = x + r_outer, y + r_outer
    draw.ellipse((cx - r_outer, cy - r_outer, cx + r_outer, cy + r_outer), outline="black", width=2)
    r_inner = size // 5
    draw.ellipse(
        (cx - r_inner, cy - r_inner, cx + r_inner, cy + r_inner), fill="black"
    )
    # plus sign
    bar = size // 4
    draw.line((cx - bar, cy, cx + bar, cy), fill="black", width=2)
    draw.line((cx, cy - bar, cx, cy + bar), fill="black", width=2)


class PsuPolarityTemplate(Template):
    meta = TemplateMeta(
        category="electronics",
        name="psu_polarity",
        summary="PSU: voltage / current / centre-positive polarity icon.",
        fields=[
            TemplateField("voltage", "Output voltage.", example="12V"),
            TemplateField("current", "Output current.", example="2A"),
            TemplateField("polarity", "'+' for centre-positive, '-' for negative.",
                          required=False, default="+"),
        ],
        default_tape=TapeWidth.MM_12,
    )

    def render(self, data: dict, tape: TapeWidth) -> Image.Image:
        v = str(data["voltage"])
        i = str(data["current"])
        pol = str(data.get("polarity") or "+")

        geom = geometry_for(tape)
        text = f"{v} / {i}"
        font = fit_text_to_box(text, mm_to_dots(80), geom.print_pins - 4, DEFAULT_BOLD)
        t_w, t_h = text_size(text, font)

        icon_size = geom.print_pins - 4
        length_dots = t_w + icon_size + mm_to_dots(5)
        canvas = LabelCanvas.create(tape, length_mm=length_dots * 25.4 / 180)

        # Text left, icon right
        canvas.draw.text((mm_to_dots(1), (geom.print_pins - t_h) // 2), text,
                         fill="black", font=font)
        icon_x = canvas.length_dots - icon_size - mm_to_dots(1)
        _draw_center_positive_icon(canvas.draw, icon_x, 2, icon_size)
        if pol != "+":
            # overlay minus mark in corner (we don't over-engineer centre-negative)
            canvas.draw.text((icon_x, canvas.height_dots - mm_to_dots(3)), "neg",
                             fill="black", font=font)
        return canvas.image
