"""Tool tag — tool name + owning project."""

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


class ToolTagTemplate(Template):
    meta = TemplateMeta(
        category="three_d_printing",
        name="tool_tag",
        summary="Tool tag: tool + owning project.",
        fields=[
            TemplateField("tool", "Tool name.", example="Calipers"),
            TemplateField("owner", "Owning person or project.", required=False,
                          example="aes / 3d-printing"),
        ],
        default_tape=TapeWidth.MM_12,
    )

    def render(self, data: dict, tape: TapeWidth) -> Image.Image:
        tool = str(data["tool"]).upper()
        owner = data.get("owner")

        geom = geometry_for(tape)
        if owner:
            top_h = int(geom.print_pins * 0.60)
            bot_h = geom.print_pins - top_h - 2
        else:
            top_h = geom.print_pins - 4
            bot_h = 0

        name_font = fit_text_to_box(tool, mm_to_dots(100), top_h, DEFAULT_BOLD)
        n_w, _ = text_size(tool, name_font)

        if owner:
            sub_font = load_font(DEFAULT_FONT, bot_h)
            s_w, _ = text_size(owner, sub_font)
        else:
            s_w = 0

        length_dots = max(n_w, s_w) + mm_to_dots(6)
        canvas = LabelCanvas.create(tape, length_mm=length_dots * 25.4 / 180)

        canvas.draw.text(((canvas.length_dots - n_w) // 2, 2), tool, fill="black", font=name_font)
        if owner:
            canvas.draw.text(((canvas.length_dots - s_w) // 2, top_h + 2), str(owner),
                             fill="black", font=sub_font)
        return canvas.image
