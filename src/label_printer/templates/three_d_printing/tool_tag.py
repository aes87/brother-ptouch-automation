"""Tool tag — tool name + optional owner."""

from __future__ import annotations

from PIL import Image

from label_printer.engine.layout import (
    DEFAULT_BOLD,
    DEFAULT_FONT,
    LabelCanvas,
    TwoLineLayout,
    draw_row,
    fit_text_to_box,
    fit_text_to_height,
    load_font,
    mm_to_dots,
    text_width,
)
from label_printer.tape import TapeWidth, geometry_for
from label_printer.templates.base import Template, TemplateField, TemplateMeta


class ToolTagTemplate(Template):
    meta = TemplateMeta(
        category="three_d_printing",
        name="tool_tag",
        summary="Tool tag: tool name + optional owner.",
        fields=[
            TemplateField("tool", "Tool name.", example="Calipers"),
            TemplateField("owner", "Owning person or project.", required=False,
                          example="aes / 3d-printing"),
        ],
        default_tape=TapeWidth.MM_12,
    )

    def render(self, data: dict, tape: TapeWidth) -> Image.Image:
        tool = str(data["tool"])
        owner = data.get("owner")

        if owner:
            layout = TwoLineLayout(tape=tape)
            name_font = fit_text_to_box(tool, mm_to_dots(100), layout.primary_h, DEFAULT_BOLD)
            sub_font = load_font(DEFAULT_FONT, layout.secondary_h - 2)
            length = max(text_width(tool, name_font),
                         text_width(str(owner), sub_font)) + mm_to_dots(6)
            canvas = LabelCanvas.create(tape, length_mm=length * 25.4 / 180)
            draw_row(canvas, tool, name_font, layout.primary_y)
            draw_row(canvas, str(owner), sub_font, layout.secondary_y)
        else:
            geom = geometry_for(tape)
            name_font = fit_text_to_height(tool, geom.print_pins - 4, DEFAULT_BOLD)
            length = text_width(tool, name_font) + mm_to_dots(6)
            canvas = LabelCanvas.create(tape, length_mm=length * 25.4 / 180)
            draw_row(canvas, tool, name_font, 2)
        return canvas.image
