"""Component bin — value + footprint + optional tolerance."""

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


class ComponentBinTemplate(Template):
    meta = TemplateMeta(
        category="electronics",
        name="component_bin",
        summary="Parts-bin label: value + footprint + optional tolerance.",
        fields=[
            TemplateField("value", "Component value.", example="10kΩ"),
            TemplateField("footprint", "Package.", example="0805"),
            TemplateField("tolerance", "Tolerance.", required=False, example="1%"),
        ],
        default_tape=TapeWidth.MM_12,
    )

    def render(self, data: dict, tape: TapeWidth) -> Image.Image:
        value = str(data["value"])
        fp = str(data["footprint"])
        tol = data.get("tolerance")

        sub = f"{fp}" + (f" · {tol}" if tol else "")
        layout = TwoLineLayout(tape=tape, secondary_ratio=0.32)

        value_font = fit_text_to_box(value, mm_to_dots(80), layout.primary_h, DEFAULT_BOLD)
        sub_font = load_font(DEFAULT_FONT, layout.secondary_h - 2)

        length = max(text_width(value, value_font), text_width(sub, sub_font)) + mm_to_dots(5)
        canvas = LabelCanvas.create(tape, length_mm=length * 25.4 / 180)

        draw_row(canvas, value, value_font, layout.primary_y)
        draw_row(canvas, sub, sub_font, layout.secondary_y)
        return canvas.image
