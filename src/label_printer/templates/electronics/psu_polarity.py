"""PSU polarity — voltage / current / polarity icon."""

from __future__ import annotations

from PIL import Image, ImageDraw

from label_printer.engine.fonts import BITMAP_THRESHOLD_PX, pick_font
from label_printer.engine.layout import (
    DEFAULT_BOLD,
    LabelCanvas,
    descender_max,
    draw_text,
    fit_text_to_box,
    mm_to_dots,
    text_width,
)
from label_printer.tape import TapeWidth, geometry_for
from label_printer.templates.base import Template, TemplateField, TemplateMeta


def _draw_center_positive_icon(draw: ImageDraw.ImageDraw, x: int, y: int, size: int) -> None:
    """IEC 60417-5926 'centre positive' pictogram."""
    r_outer = size // 2
    cx, cy = x + r_outer, y + r_outer
    draw.ellipse((cx - r_outer, cy - r_outer, cx + r_outer, cy + r_outer), outline="black", width=2)
    r_inner = size // 5
    draw.ellipse((cx - r_inner, cy - r_inner, cx + r_inner, cy + r_inner), fill="black")
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
            TemplateField(
                "polarity",
                "'+' for centre-positive, '-' for negative.",
                required=False,
                default="+",
            ),
        ],
        default_tape=TapeWidth.MM_12,
    )

    def render(self, data: dict, tape: TapeWidth) -> Image.Image:
        v = str(data["voltage"])
        i = str(data["current"])
        pol = str(data.get("polarity") or "+")

        geom = geometry_for(tape)
        text = f"{v} / {i}"
        avail_h = geom.print_pins - 4
        # Size the text via the outline-fit search, but if the resulting cap
        # height lands in the small-glyph regime swap in the matching Spleen
        # bitmap cut so stems threshold cleanly at 1-bit.
        sized = fit_text_to_box(text, mm_to_dots(80), avail_h, DEFAULT_BOLD)
        cap_h = sized.getbbox("A")[3] - sized.getbbox("A")[1]
        font = pick_font(cap_h, bold=True) if cap_h <= BITMAP_THRESHOLD_PX else sized
        t_w = text_width(text, font)

        icon_size = geom.print_pins - 6
        length = t_w + icon_size + mm_to_dots(6)
        canvas = LabelCanvas.create(tape, length_mm=length * 25.4 / 180)

        # Vertically center the cap height inside the print area, then
        # baseline-anchor so descenders aren't reserved as empty padding.
        desc = descender_max(font)
        actual_cap_h = font.getbbox("A")[3] - font.getbbox("A")[1]
        text_top = max(0, (geom.print_pins - actual_cap_h) // 2)
        baseline_y = text_top + actual_cap_h
        draw_text(canvas, text, font, mm_to_dots(1), baseline_y, anchor="ls")

        icon_x = canvas.length_dots - icon_size - mm_to_dots(1)
        icon_y = (geom.print_pins - icon_size) // 2
        _draw_center_positive_icon(canvas.draw, icon_x, icon_y, icon_size)
        if pol != "+":
            # "neg" caption is small — use the same baseline-anchored draw
            # so it sits flush with the bottom edge.
            draw_text(canvas, "neg", font, icon_x, canvas.height_dots - desc, anchor="ls")
        return canvas.image
