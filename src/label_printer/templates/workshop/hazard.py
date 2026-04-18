"""Hazard label — large pictogram on the left + hazard text + optional code."""

from __future__ import annotations

from PIL import Image

from label_printer.engine.layout import (
    DEFAULT_BOLD,
    DEFAULT_FONT,
    LabelCanvas,
    draw_text,
    fit_text_to_box,
    load_font,
    mm_to_dots,
    text_width,
)
from label_printer.tape import TapeWidth, geometry_for
from label_printer.templates.base import Template, TemplateField, TemplateMeta

_KNOWN_ICONS = {
    "warning": "alert-triangle",
    "flammable": "flame",
    "biohazard": "biohazard",
    "electrical": "zap",
    "chemical": "droplets",
    "sharp": "scissors",
    "hot": "flame",
    "cold": "snowflake",
    "radiation": "alert-triangle",  # fallback if radiation icon missing
}


class HazardTemplate(Template):
    meta = TemplateMeta(
        category="workshop",
        name="hazard",
        summary="Hazard label: pictogram + hazard type + optional code reference.",
        fields=[
            TemplateField(
                "hazard",
                "Hazard keyword — one of: warning, flammable, biohazard, electrical, "
                "chemical, sharp, hot, cold, radiation.",
                example="flammable",
            ),
            TemplateField("text", "Hazard description.", example="ACETONE"),
            TemplateField("code", "Optional reference code (MSDS section, GHS code…).",
                          required=False, example="GHS02"),
            TemplateField("icon", "Override the default icon.", required=False,
                          example="flame"),
        ],
        default_tape=TapeWidth.MM_12,
    )

    def render(self, data: dict, tape: TapeWidth) -> Image.Image:
        hazard = str(data["hazard"]).lower()
        text = str(data["text"])
        code = data.get("code")
        icon_name = data.get("icon") or _KNOWN_ICONS.get(hazard, "alert-triangle")

        from label_printer.engine.icons import IconEngineUnavailable, load_icon

        geom = geometry_for(tape)
        icon_size = geom.print_pins - 4
        try:
            icon_img = load_icon(icon_name, icon_size)
        except IconEngineUnavailable as e:
            raise ValueError(str(e)) from e

        primary_h = int(geom.print_pins * 0.62)
        secondary_h = geom.print_pins - primary_h - 4
        icon_offset = icon_size + mm_to_dots(2)

        text_font = fit_text_to_box(text, mm_to_dots(100), primary_h, DEFAULT_BOLD)
        sub_text = code or hazard.upper()
        sub_font = load_font(DEFAULT_FONT, max(10, secondary_h - 2))

        text_w_pixels = max(text_width(text, text_font), text_width(sub_text, sub_font))
        length_dots = icon_offset + text_w_pixels + mm_to_dots(6)
        canvas = LabelCanvas.create(tape, length_mm=length_dots * 25.4 / 180)

        canvas.image.paste(icon_img, (mm_to_dots(1), 2))

        # Main text
        w = text_width(text, text_font)
        x = icon_offset + (canvas.length_dots - icon_offset - w) // 2
        draw_text(canvas, text, text_font, x, 2, anchor="lt")
        # Sub text
        sw = text_width(sub_text, sub_font)
        sx = icon_offset + (canvas.length_dots - icon_offset - sw) // 2
        draw_text(canvas, sub_text, sub_font, sx, primary_h + 4, anchor="lt")
        return canvas.image
