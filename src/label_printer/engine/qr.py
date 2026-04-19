"""Shared QR-code rendering primitive used across templates."""

from __future__ import annotations

import qrcode
from PIL import Image
from qrcode.constants import ERROR_CORRECT_M


def render_qr(payload: str, pixels: int) -> Image.Image:
    """Render ``payload`` as a QR code and scale it to exactly ``pixels`` square, 1-bit.

    Uses medium error correction (~15% redundancy) — the documented default
    for labels that may be photographed under imperfect conditions.
    """
    qr = qrcode.QRCode(version=None, error_correction=ERROR_CORRECT_M, box_size=4, border=1)
    qr.add_data(payload)
    qr.make(fit=True)
    big = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    return big.resize((pixels, pixels), Image.Resampling.NEAREST)
