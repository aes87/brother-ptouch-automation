"""Layout helpers for composing labels at 180 DPI.

All geometry is in dots (@180 DPI). Callers can use ``mm_to_dots()`` at the
boundary if they want to think in millimetres.

Sizing uses ``font.getmetrics()`` (ascent + descent) rather than the tight
glyph bbox, so reserving N dots for a line actually gives N dots including
descender space. Drawing uses explicit anchors so positions line up with
the reserved box instead of drifting by the font's internal em padding.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from label_printer.constants import DPI
from label_printer.tape import TapeWidth, geometry_for

FONTS_DIR = Path(__file__).resolve().parents[3] / "assets" / "fonts"
DEFAULT_FONT = FONTS_DIR / "DejaVuSans.ttf"
DEFAULT_BOLD = FONTS_DIR / "DejaVuSans-Bold.ttf"
DEFAULT_MONO = FONTS_DIR / "DejaVuSansMono.ttf"


def mm_to_dots(mm: float) -> int:
    return int(round(mm * DPI / 25.4))


def dots_to_mm(dots: int) -> float:
    return dots * 25.4 / DPI


@dataclass
class LabelCanvas:
    """A blank label image sized for a given tape width and length.

    Coordinates are dots @180 DPI. Origin is top-left; tape feeds left-to-right
    through the printer, so ``width`` is the label's long axis.
    """

    tape: TapeWidth
    length_dots: int
    image: Image.Image
    draw: ImageDraw.ImageDraw

    @classmethod
    def create(cls, tape: TapeWidth, length_mm: float) -> LabelCanvas:
        geom = geometry_for(tape)
        length_dots = mm_to_dots(length_mm)
        image = Image.new("RGB", (length_dots, geom.print_pins), "white")
        return cls(tape=tape, length_dots=length_dots, image=image, draw=ImageDraw.Draw(image))

    @property
    def height_dots(self) -> int:
        return self.image.height


def load_font(path: str | Path | None, size_dots: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(path or DEFAULT_FONT), size=size_dots)


def font_line_height(font: ImageFont.FreeTypeFont) -> int:
    """Total vertical space a line of this font occupies (ascent + descent)."""
    ascent, descent = font.getmetrics()
    return ascent + descent


def text_width(text: str, font: ImageFont.FreeTypeFont) -> int:
    """Rendered width in dots."""
    return int(font.getlength(text))


def text_size(text: str, font: ImageFont.FreeTypeFont) -> tuple[int, int]:
    """(width, full-line-height) — reserves descender space even for text without descenders."""
    return text_width(text, font), font_line_height(font)


def fit_text_to_height(
    text: str, height_dots: int, font_path: str | Path | None = None, max_size: int = 200
) -> ImageFont.FreeTypeFont:
    """Largest font whose full line-height fits within ``height_dots``."""
    lo, hi = 6, max_size
    best = lo
    while lo <= hi:
        mid = (lo + hi) // 2
        font = load_font(font_path, mid)
        if font_line_height(font) <= height_dots:
            best = mid
            lo = mid + 1
        else:
            hi = mid - 1
    return load_font(font_path, best)


def fit_text_to_box(
    text: str, box_w: int, box_h: int, font_path: str | Path | None = None, max_size: int = 200
) -> ImageFont.FreeTypeFont:
    """Largest font where text width <= ``box_w`` AND line-height <= ``box_h``."""
    lo, hi = 6, max_size
    best = lo
    while lo <= hi:
        mid = (lo + hi) // 2
        font = load_font(font_path, mid)
        if text_width(text, font) <= box_w and font_line_height(font) <= box_h:
            best = mid
            lo = mid + 1
        else:
            hi = mid - 1
    return load_font(font_path, best)


def draw_text(
    canvas: LabelCanvas,
    text: str,
    font: ImageFont.FreeTypeFont,
    x: int,
    y: int,
    anchor: str = "lt",
) -> None:
    """Draw text with an explicit anchor.

    Default ``anchor='lt'`` means (x, y) is the top-left of the glyph bbox —
    so reserving a row that starts at y=Y draws glyphs starting exactly at Y.
    """
    canvas.draw.text((x, y), text, fill="black", font=font, anchor=anchor)


def draw_row(
    canvas: LabelCanvas,
    text: str,
    font: ImageFont.FreeTypeFont,
    y: int,
    align: str = "center",
) -> None:
    """Draw ``text`` horizontally laid-out on the canvas at vertical offset ``y``.

    ``align`` ∈ {"center", "left", "right"}. Uses anchor-based positioning so
    glyphs start at y exactly, with descenders ending at y + line_height.
    """
    if align == "center":
        x = canvas.length_dots // 2
        anchor = "mt"
    elif align == "right":
        x = canvas.length_dots - 2
        anchor = "rt"
    else:
        x = 2
        anchor = "lt"
    draw_text(canvas, text, font, x, y, anchor)


def draw_dashed_vline(canvas: LabelCanvas, x: int, dash: int = 4, gap: int = 4) -> None:
    y = 0
    while y < canvas.height_dots:
        canvas.draw.line([(x, y), (x, min(y + dash, canvas.height_dots))], fill="black", width=1)
        y += dash + gap


# Backwards-compatible alias — older code used draw_centered_text(canvas, text, font, y=...)
def draw_centered_text(
    canvas: LabelCanvas,
    text: str,
    font: ImageFont.FreeTypeFont,
    y: int | None = None,
    x: int | None = None,
) -> None:
    if y is None:
        y = (canvas.height_dots - font_line_height(font)) // 2
    if x is not None:
        draw_text(canvas, text, font, x, y, anchor="lt")
    else:
        draw_row(canvas, text, font, y, align="center")


def split_lines_to_fit(
    text: str, width_dots: int, font: ImageFont.FreeTypeFont
) -> list[str]:
    """Greedy word-wrap. Long words are kept as-is (may overflow)."""
    lines: list[str] = []
    line = ""
    for word in text.split():
        candidate = f"{line} {word}".strip()
        if text_width(candidate, font) <= width_dots:
            line = candidate
        else:
            if line:
                lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines or [""]


def render_two_line_label(
    tape: TapeWidth,
    primary: str,
    secondary: str,
    *,
    icon: str | None = None,
    primary_font: str | Path | None = None,
    secondary_font: str | Path | None = None,
    max_width_mm: float = 120.0,
    padding_mm: float = 6.0,
) -> Image.Image:
    """Render a bold-on-top, subtitle-below label with optional left-side icon.

    Shared across most template packs. Covers the common case: one headline,
    one subtitle, centered horizontally, optional Lucide icon on the left.
    Templates with unique visual needs (cable flags, PSU polarity icons,
    QR codes) stay bespoke.
    """

    layout = TwoLineLayout(tape=tape)
    p_font_path = primary_font if primary_font is not None else DEFAULT_BOLD
    s_font_path = secondary_font if secondary_font is not None else DEFAULT_FONT

    p_font = fit_text_to_box(
        primary, mm_to_dots(max_width_mm), layout.primary_h, p_font_path
    )
    s_font = load_font(s_font_path, layout.secondary_h - 2)

    from label_printer.tape import geometry_for
    geom = geometry_for(tape)
    icon_img = None
    icon_offset = 0
    if icon:
        from label_printer.engine.icons import IconEngineUnavailable, load_icon
        try:
            icon_size = geom.print_pins - 4
            icon_img = load_icon(icon, icon_size)
            icon_offset = icon_size + mm_to_dots(2)
        except IconEngineUnavailable as e:
            raise ValueError(str(e)) from e

    text_w = max(text_width(primary, p_font), text_width(secondary, s_font))
    length_dots = icon_offset + text_w + mm_to_dots(padding_mm)
    canvas = LabelCanvas.create(tape, length_mm=length_dots * 25.4 / 180)

    if icon_img is not None:
        canvas.image.paste(icon_img, (mm_to_dots(1), 2))

    if icon_offset:
        for text, font, y in (
            (primary, p_font, layout.primary_y),
            (secondary, s_font, layout.secondary_y),
        ):
            w = text_width(text, font)
            x = icon_offset + (canvas.length_dots - icon_offset - w) // 2
            draw_text(canvas, text, font, x, y, anchor="lt")
    else:
        draw_row(canvas, primary, p_font, layout.primary_y)
        draw_row(canvas, secondary, s_font, layout.secondary_y)
    return canvas.image


@dataclass(frozen=True)
class TwoLineLayout:
    """Vertical layout for a common 'big line on top, small line on bottom' label.

    For a 70-pin (12mm) tape with defaults this gives roughly:

        pad_top=2, primary=44, gap=4, secondary=18, pad_bottom=2  → 70
    """

    tape: TapeWidth
    pad_top: int = 2
    gap: int = 4
    pad_bottom: int = 2
    secondary_ratio: float = 0.28  # fraction of available height for the small line

    @property
    def available(self) -> int:
        return geometry_for(self.tape).print_pins - self.pad_top - self.gap - self.pad_bottom

    @property
    def secondary_h(self) -> int:
        return max(12, int(self.available * self.secondary_ratio))

    @property
    def primary_h(self) -> int:
        return self.available - self.secondary_h

    @property
    def primary_y(self) -> int:
        return self.pad_top

    @property
    def secondary_y(self) -> int:
        return self.pad_top + self.primary_h + self.gap
