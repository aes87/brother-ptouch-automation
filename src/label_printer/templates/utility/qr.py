"""QR code label — scan-friendly square with optional caption alongside."""

from __future__ import annotations

from PIL import Image

from label_printer.engine.fonts import BITMAP_THRESHOLD_PX, pick_font
from label_printer.engine.layout import (
    DEFAULT_BOLD,
    LabelCanvas,
    draw_text,
    fit_text_to_box,
    mm_to_dots,
    text_width,
)
from label_printer.engine.qr import render_qr
from label_printer.tape import TapeWidth, geometry_for
from label_printer.templates.base import Template, TemplateField, TemplateMeta


class QrTemplate(Template):
    handles_extras = frozenset({"link"})
    meta = TemplateMeta(
        category="utility",
        name="qr",
        summary="QR code on the left, optional caption on the right.",
        fields=[
            TemplateField("data", "URL or text to encode.", example="https://example.com"),
            TemplateField(
                "caption",
                "Optional caption text alongside the code.",
                required=False,
                example="Wi-Fi guest",
            ),
        ],
        default_tape=TapeWidth.MM_12,
    )

    def render(self, data: dict, tape: TapeWidth) -> Image.Image:
        payload = str(data["data"])
        caption = data.get("caption")

        geom = geometry_for(tape)
        qr_size = geom.print_pins
        qr_img = render_qr(payload, qr_size)

        caption_gap = mm_to_dots(2) if caption else 0
        if caption:
            avail_h = geom.print_pins - 4
            sized = fit_text_to_box(str(caption), mm_to_dots(80), avail_h, DEFAULT_BOLD)
            cap_h = sized.getbbox("A")[3] - sized.getbbox("A")[1]
            # Captions next to QR codes are usually small at 12mm — swap to
            # Spleen if we're under the bitmap threshold.
            font = pick_font(cap_h, bold=True) if cap_h <= BITMAP_THRESHOLD_PX else sized
            caption_w = text_width(str(caption), font)
        else:
            caption_w = 0

        length = qr_size + caption_gap + caption_w + mm_to_dots(2)
        canvas = LabelCanvas.create(tape, length_mm=length * 25.4 / 180)
        canvas.image.paste(qr_img, (0, 0))

        if caption:
            text_x = qr_size + caption_gap
            # Center the cap height vertically, then baseline-anchor.
            actual_cap_h = font.getbbox("A")[3] - font.getbbox("A")[1]
            text_top = max(0, (geom.print_pins - actual_cap_h) // 2)
            baseline_y = text_top + actual_cap_h
            draw_text(canvas, str(caption), font, text_x, baseline_y, anchor="ls")
        return canvas.image
