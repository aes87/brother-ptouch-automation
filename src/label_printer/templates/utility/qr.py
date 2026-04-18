"""QR code label — scan-friendly square with optional caption alongside."""

from __future__ import annotations

import qrcode
from PIL import Image
from qrcode.constants import ERROR_CORRECT_M

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


def _render_qr(data: str, pixels: int) -> Image.Image:
    """Render a QR code and scale it to exactly `pixels` square, 1-bit."""
    qr = qrcode.QRCode(version=None, error_correction=ERROR_CORRECT_M, box_size=4, border=1)
    qr.add_data(data)
    qr.make(fit=True)
    big = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    return big.resize((pixels, pixels), Image.Resampling.NEAREST)


class QrTemplate(Template):
    meta = TemplateMeta(
        category="utility",
        name="qr",
        summary="QR code on the left, optional caption on the right.",
        fields=[
            TemplateField("data", "URL or text to encode.", example="https://example.com"),
            TemplateField("caption", "Optional caption text alongside the code.",
                          required=False, example="Wi-Fi guest"),
        ],
        default_tape=TapeWidth.MM_12,
    )

    def render(self, data: dict, tape: TapeWidth) -> Image.Image:
        payload = str(data["data"])
        caption = data.get("caption")

        geom = geometry_for(tape)
        qr_size = geom.print_pins
        qr_img = _render_qr(payload, qr_size)

        caption_gap = mm_to_dots(2) if caption else 0
        if caption:
            avail_h = geom.print_pins - 4
            font = fit_text_to_box(str(caption), mm_to_dots(80), avail_h, DEFAULT_BOLD)
            caption_w = text_width(str(caption), font)
        else:
            caption_w = 0

        length = qr_size + caption_gap + caption_w + mm_to_dots(2)
        canvas = LabelCanvas.create(tape, length_mm=length * 25.4 / 180)
        canvas.image.paste(qr_img, (0, 0))

        if caption:
            text_x = qr_size + caption_gap
            text_y = (geom.print_pins - font_line_height(font)) // 2
            draw_text(canvas, str(caption), font, text_x, text_y, anchor="lt")
        return canvas.image
