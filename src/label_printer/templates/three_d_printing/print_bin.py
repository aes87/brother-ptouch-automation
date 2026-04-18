"""Print bin — part name + project + quantity."""

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


class PrintBinTemplate(Template):
    meta = TemplateMeta(
        category="three_d_printing",
        name="print_bin",
        summary="Print bin label: part name + project + quantity.",
        fields=[
            TemplateField("part", "Printed part name.", example="Fan tub clip v2"),
            TemplateField("project", "Project it belongs to.", required=False,
                          example="fan-tub-adapter"),
            TemplateField("qty", "Quantity in the bin.", required=False, default="1"),
        ],
        default_tape=TapeWidth.MM_12,
    )

    def render(self, data: dict, tape: TapeWidth) -> Image.Image:
        part = str(data["part"]).upper()
        project = data.get("project")
        qty = str(data.get("qty") or "1")

        geom = geometry_for(tape)
        top_h = int(geom.print_pins * 0.60)
        bot_h = geom.print_pins - top_h - 2

        name_font = fit_text_to_box(part, mm_to_dots(120), top_h, DEFAULT_BOLD)
        n_w, _ = text_size(part, name_font)

        sub_parts = [f"×{qty}"]
        if project:
            sub_parts.append(project)
        sub = " · ".join(sub_parts)
        sub_font = load_font(DEFAULT_FONT, bot_h)
        s_w, _ = text_size(sub, sub_font)

        length_dots = max(n_w, s_w) + mm_to_dots(6)
        canvas = LabelCanvas.create(tape, length_mm=length_dots * 25.4 / 180)

        canvas.draw.text(((canvas.length_dots - n_w) // 2, 0), part, fill="black", font=name_font)
        canvas.draw.text(((canvas.length_dots - s_w) // 2, top_h + 2), sub,
                         fill="black", font=sub_font)
        return canvas.image
