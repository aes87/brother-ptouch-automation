"""Filament spool — material + color + brand + date-opened + temp range."""

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


class FilamentSpoolTemplate(Template):
    meta = TemplateMeta(
        category="three_d_printing",
        name="filament_spool",
        summary="Filament spool label: material + colour + brand + opened + temps.",
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
        material = str(data["material"]).upper()
        color = str(data["color"])
        brand = str(data["brand"])
        opened = str(data["opened"])
        nozzle = data.get("nozzle_temp")
        bed = data.get("bed_temp")

        geom = geometry_for(tape)
        top_h = int(geom.print_pins * 0.55)
        bot_h = geom.print_pins - top_h - 2

        top_text = f"{material} · {color}"
        bot_parts = [brand, f"opened {opened}"]
        if nozzle:
            bot_parts.append(f"N {nozzle}°C")
        if bed:
            bot_parts.append(f"B {bed}°C")
        bot_text = " · ".join(bot_parts)

        top_font = fit_text_to_box(top_text, mm_to_dots(120), top_h, DEFAULT_BOLD)
        t_w, _ = text_size(top_text, top_font)
        bot_font = load_font(DEFAULT_FONT, bot_h)
        b_w, _ = text_size(bot_text, bot_font)

        length_dots = max(t_w, b_w) + mm_to_dots(6)
        canvas = LabelCanvas.create(tape, length_mm=length_dots * 25.4 / 180)

        canvas.draw.text(((canvas.length_dots - t_w) // 2, 0), top_text,
                         fill="black", font=top_font)
        canvas.draw.text(((canvas.length_dots - b_w) // 2, top_h + 2), bot_text,
                         fill="black", font=bot_font)
        return canvas.image
