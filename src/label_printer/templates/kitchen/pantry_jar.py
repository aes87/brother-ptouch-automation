"""Pantry jar label — bold item name, small purchase + optional expiry, optional icon."""

from __future__ import annotations

from PIL import Image

from label_printer.engine.layout import (
    DEFAULT_BOLD,
    DEFAULT_FONT,
    LabelCanvas,
    TwoLineLayout,
    draw_row,
    draw_text,
    fit_text_to_box,
    load_font,
    mm_to_dots,
    text_width,
)
from label_printer.tape import TapeWidth, geometry_for
from label_printer.templates.base import Template, TemplateField, TemplateMeta


class PantryJarTemplate(Template):
    meta = TemplateMeta(
        category="kitchen",
        name="pantry_jar",
        summary="Pantry item with purchase date and optional expiry (+ optional icon).",
        fields=[
            TemplateField("name", "Item name (e.g. 'AP Flour', 'Brown Rice').",
                          example="AP Flour"),
            TemplateField("purchased", "Purchase date (YYYY-MM-DD).", example="2026-04-19"),
            TemplateField("expires", "Optional expiry date.", required=False,
                          example="2027-04-19"),
            TemplateField(
                "icon",
                "Optional Lucide icon name to paste on the left (e.g. 'wheat' for flour, "
                "'egg' for eggs, 'leaf' for herbs). Requires the [icons] extra.",
                required=False, example="wheat",
            ),
        ],
        default_tape=TapeWidth.MM_12,
    )

    def render(self, data: dict, tape: TapeWidth) -> Image.Image:
        name = str(data["name"])
        purchased = str(data["purchased"])
        expires = data.get("expires")
        icon_name = data.get("icon")

        sub = f"{purchased}" + (f" · exp {expires}" if expires else "")
        layout = TwoLineLayout(tape=tape)

        max_w = mm_to_dots(120)
        name_font = fit_text_to_box(name, max_w, layout.primary_h, DEFAULT_BOLD)
        sub_font = load_font(DEFAULT_FONT, layout.secondary_h - 2)

        geom = geometry_for(tape)
        icon_size = geom.print_pins - 4  # square, fills tape height with margin
        icon_img = None
        icon_offset = 0
        if icon_name:
            from label_printer.engine.icons import IconEngineUnavailable, load_icon
            try:
                icon_img = load_icon(str(icon_name), icon_size)
                icon_offset = icon_size + mm_to_dots(2)
            except IconEngineUnavailable as e:
                raise ValueError(str(e)) from e

        text_w = max(text_width(name, name_font), text_width(sub, sub_font))
        length_dots = icon_offset + text_w + mm_to_dots(6)
        canvas = LabelCanvas.create(tape, length_mm=length_dots * 25.4 / 180)

        if icon_img is not None:
            canvas.image.paste(icon_img, (mm_to_dots(1), 2))

        # Nudge text rightward by icon_offset; draw_row centres across the canvas
        # by default, so we draw explicitly when an icon is present.
        if icon_offset:
            for text, font, y in (
                (name, name_font, layout.primary_y),
                (sub, sub_font, layout.secondary_y),
            ):
                w = text_width(text, font)
                x = icon_offset + (canvas.length_dots - icon_offset - w) // 2
                draw_text(canvas, text, font, x, y, anchor="lt")
        else:
            draw_row(canvas, name, name_font, layout.primary_y)
            draw_row(canvas, sub, sub_font, layout.secondary_y)
        return canvas.image
