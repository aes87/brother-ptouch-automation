"""Font registry: pick a font tuned for the target pixel size.

At 180 DPI a 12mm tape gives ~70 printable pins. Most templates put a 12-18
dot subtitle on the bottom row, which is the regime where outline fonts
(DejaVu, etc.) start to look ragged: their hinted glyphs land on different
sub-pixel offsets, so when we threshold to 1-bit some stems get one pixel
wide and others get two. The fix is to use a *bitmap* font whose glyphs are
already pixel-tuned at the exact rendering size.

Spleen (BSD 2-clause) ships native bitmap glyphs at 6x12, 8x16, 12x24, and
16x32. Pillow can load these via the OpenType-bitmap (.otb) wrappers as long
as we ask for them at their native pixel size. Outside that small set we
fall back to DejaVu Sans Bold scaled to the requested cap-height — the
existing behaviour.

Usage:

    font = pick_font(target_pixel_height=14)            # → Spleen 8x16
    font = pick_font(target_pixel_height=14, bold=True) # → Spleen 8x16 (no weight option)
    font = pick_font(target_pixel_height=24)            # → DejaVu Bold @ 24

The `BITMAP_THRESHOLD_PX` constant pins the cutoff. Above that, outline
fonts look fine and we want their proportional spacing back.
"""

from __future__ import annotations

from pathlib import Path

from PIL import ImageFont

from label_printer.engine.layout import (
    DEFAULT_BOLD,
    DEFAULT_FONT,
    FONTS_DIR,
    load_font,
)

# Outline fonts above this cap-height (in pixels) are sharp enough — using
# Spleen here would lose the proportional letterforms we expect for big text.
# 32 covers all four bundled Spleen cuts (6x12, 8x16, 12x24, 16x32). Subtitle
# rows on 12mm and 24mm tape both fall under this ceiling and want pixel-
# tuned glyphs; the headline row sails well past 32 and stays on DejaVu.
BITMAP_THRESHOLD_PX = 32

SPLEEN_DIR = FONTS_DIR / "bitmap" / "spleen"

# Pillow loads each .otb at *exactly* its native pixel size.
# Cap heights are the y2 of bbox('A'), which equals the second number in the
# Spleen name (12, 16, 24, 32). Line height matches the same number.
_SPLEEN_NATIVE_SIZES: tuple[tuple[int, str], ...] = (
    (12, "spleen-6x12.otb"),
    (16, "spleen-8x16.otb"),
    (24, "spleen-12x24.otb"),
    (32, "spleen-16x32.otb"),
)


def _spleen_path(filename: str) -> Path:
    return SPLEEN_DIR / filename


def _bitmap_for(target_h: int) -> ImageFont.FreeTypeFont | None:
    """Return the largest Spleen variant whose native height fits target_h.

    Returns None if no bitmap variant fits (target_h < smallest native = 12).
    """
    chosen: tuple[int, str] | None = None
    for native_h, name in _SPLEEN_NATIVE_SIZES:
        if native_h <= target_h:
            chosen = (native_h, name)
        else:
            break
    if chosen is None:
        return None
    native_h, name = chosen
    path = _spleen_path(name)
    if not path.exists():
        return None
    return ImageFont.truetype(str(path), size=native_h)


def pick_font(target_pixel_height: int, *, bold: bool = False) -> ImageFont.FreeTypeFont:
    """Best-fit font for a given target pixel height.

    For small text (<= ``BITMAP_THRESHOLD_PX`` cap height), prefer a Spleen
    bitmap glyph cut at the largest native size that fits. Above that
    threshold (or when no Spleen variant fits), fall back to DejaVu Sans —
    Bold cut if ``bold`` is set or if the height is small enough that a
    regular-weight stroke would hairline at 1-bit.
    """
    if target_pixel_height <= BITMAP_THRESHOLD_PX:
        bitmap = _bitmap_for(target_pixel_height)
        if bitmap is not None:
            return bitmap

    # Outline fallback: bold by default below 14px because regular DejaVu
    # stems disappear when thresholded at small sizes.
    use_bold = bold or target_pixel_height <= 14
    path = DEFAULT_BOLD if use_bold else DEFAULT_FONT
    return load_font(path, max(6, target_pixel_height))


def is_bitmap_font(font: ImageFont.FreeTypeFont) -> bool:
    """True if ``font`` is one of the bundled Spleen bitmap cuts."""
    try:
        path = Path(font.path)
    except AttributeError:
        return False
    try:
        return path.is_relative_to(SPLEEN_DIR)
    except (AttributeError, ValueError):
        return SPLEEN_DIR in path.parents
