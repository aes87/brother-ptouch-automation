"""Filament spool — material + colour + brand + date opened + temps."""

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


class FilamentSpoolTemplate(Template):
    meta = TemplateMeta(
        category="three_d_printing",
        name="filament_spool",
        summary="Filament spool: material + colour + brand + opened + optional temps.",
        fields=[
            TemplateField("material", "Filament material.", example="PLA"),
            TemplateField("color", "Colour name.", example="Obsidian Black"),
            TemplateField("brand", "Brand name.", example="Bambu"),
            TemplateField("opened", "Date opened.", example="2026-04-19"),
            TemplateField("nozzle_temp", "Nozzle temp range °C.", required=False,
                          example="200-220"),
            TemplateField("bed_temp", "Bed temp °C.", required=False, example="60"),
        ],
        default_tape=TapeWidth.MM_12,
    )

    def render(self, data: dict, tape: TapeWidth) -> Image.Image:
        material = str(data["material"])
        color = str(data["color"])
        brand = str(data["brand"])
        opened = str(data["opened"])
        nozzle = data.get("nozzle_temp")
        bed = data.get("bed_temp")

        top = f"{material} · {color}"
        bot_parts = [brand, f"opened {opened}"]
        if nozzle:
            bot_parts.append(f"N {nozzle}°C")
        if bed:
            bot_parts.append(f"B {bed}°C")
        bot = " · ".join(bot_parts)

        layout = TwoLineLayout(tape=tape, secondary_ratio=0.33)
        top_font = fit_text_to_box(top, mm_to_dots(140), layout.primary_h, DEFAULT_BOLD)
        bot_font = load_font(DEFAULT_FONT, layout.secondary_h - 2)

        length = max(text_width(top, top_font), text_width(bot, bot_font)) + mm_to_dots(8)
        canvas = LabelCanvas.create(tape, length_mm=length * 25.4 / 180)

        draw_row(canvas, top, top_font, layout.primary_y)
        draw_row(canvas, bot, bot_font, layout.secondary_y)
        return canvas.image
