"""Image label — a small bitmap scaled to tape height, with optional caption."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from label_printer.engine.layout import (
    DEFAULT_BOLD,
    LabelCanvas,
    draw_text,
    fit_text_to_box,
    font_line_height,
    mm_to_dots,
    text_width,
)
from label_printer.tape import TapeWidth, geometry_for
from label_printer.templates.base import Template, TemplateField, TemplateMeta


class ImageLabelTemplate(Template):
    meta = TemplateMeta(
        category="utility",
        name="image",
        summary="Bitmap scaled to tape height, optionally with a caption on the right.",
        fields=[
            TemplateField("path", "Path to the image file (PNG/JPEG/etc.).",
                          example="logo.png"),
            TemplateField("caption", "Optional caption text to print next to the image.",
                          required=False, example="aes87"),
            TemplateField("threshold", "Monochrome threshold 0-255 (default 128).",
                          required=False, default=128),
        ],
        default_tape=TapeWidth.MM_12,
    )

    def render(self, data: dict, tape: TapeWidth) -> Image.Image:
        path = Path(str(data["path"])).expanduser()
        caption = data.get("caption")
        threshold = int(data.get("threshold") or 128)

        geom = geometry_for(tape)
        src = Image.open(path)
        # Fit to tape height, preserve aspect ratio
        scale = geom.print_pins / src.height
        img_w = max(1, int(round(src.width * scale)))
        resized = src.resize((img_w, geom.print_pins), Image.Resampling.LANCZOS)

        # Monochrome: ink where the pixel is darker than threshold (alpha-aware).
        if resized.mode == "RGBA":
            bg = Image.new("RGB", resized.size, (255, 255, 255))
            bg.paste(resized, mask=resized.split()[-1])
            resized = bg
        gray = resized.convert("L")
        mono = gray.point(lambda v: 0 if v < threshold else 255, mode="1").convert("RGB")

        gap = mm_to_dots(2) if caption else 0
        if caption:
            avail_h = geom.print_pins - 4
            font = fit_text_to_box(str(caption), mm_to_dots(100), avail_h, DEFAULT_BOLD)
            caption_w = text_width(str(caption), font)
        else:
            caption_w = 0

        length = img_w + gap + caption_w + mm_to_dots(2)
        canvas = LabelCanvas.create(tape, length_mm=length * 25.4 / 180)
        canvas.image.paste(mono, (0, 0))
        if caption:
            text_x = img_w + gap
            text_y = (geom.print_pins - font_line_height(font)) // 2
            draw_text(canvas, str(caption), font, text_x, text_y, anchor="lt")
        return canvas.image
