"""Component bin — value + footprint (+ optional tolerance)."""

from __future__ import annotations

from PIL import Image

from label_printer.engine.layout import (
    DEFAULT_BOLD,
    DEFAULT_FONT,
    LabelCanvas,
    fit_text_to_box,
    load_font,
    mm_to_dots,
    text_size,
)
from label_printer.tape import TapeWidth, geometry_for
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

        geom = geometry_for(tape)
        value_h = int(geom.print_pins * 0.65)
        sub_h = geom.print_pins - value_h - 2

        value_font = fit_text_to_box(value, mm_to_dots(80), value_h, DEFAULT_BOLD)
        v_w, _ = text_size(value, value_font)

        sub = f"{fp}" + (f" · {tol}" if tol else "")
        sub_font = load_font(DEFAULT_FONT, sub_h)
        sub_w, _ = text_size(sub, sub_font)

        length_dots = max(v_w, sub_w) + mm_to_dots(4)
        canvas = LabelCanvas.create(tape, length_mm=length_dots * 25.4 / 180)
        canvas.draw.text(((canvas.length_dots - v_w) // 2, 0), value, fill="black", font=value_font)
        canvas.draw.text(((canvas.length_dots - sub_w) // 2, value_h + 2), sub, fill="black",
                         font=sub_font)
        return canvas.image
