"""Print bin — part name + optional project + quantity."""

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


class PrintBinTemplate(Template):
    meta = TemplateMeta(
        category="three_d_printing",
        name="print_bin",
        summary="Print bin label: part name + optional project + quantity.",
        fields=[
            TemplateField("part", "Printed part name.", example="Fan tub clip v2"),
            TemplateField("project", "Project it belongs to.", required=False,
                          example="fan-tub-adapter"),
            TemplateField("qty", "Quantity in the bin.", required=False, default="1"),
        ],
        default_tape=TapeWidth.MM_12,
    )

    def render(self, data: dict, tape: TapeWidth) -> Image.Image:
        part = str(data["part"])
        project = data.get("project")
        qty = str(data.get("qty") or "1")

        sub_parts = [f"×{qty}"]
        if project:
            sub_parts.append(project)
        sub = " · ".join(sub_parts)

        layout = TwoLineLayout(tape=tape)
        name_font = fit_text_to_box(part, mm_to_dots(120), layout.primary_h, DEFAULT_BOLD)
        sub_font = load_font(DEFAULT_FONT, layout.secondary_h - 2)

        length = max(text_width(part, name_font), text_width(sub, sub_font)) + mm_to_dots(6)
        canvas = LabelCanvas.create(tape, length_mm=length * 25.4 / 180)

        draw_row(canvas, part, name_font, layout.primary_y)
        draw_row(canvas, sub, sub_font, layout.secondary_y)
        return canvas.image
