"""Layout helpers for composing labels at 180 DPI.

All geometry is in dots (@180 DPI). Callers can use mm_to_dots() at the
boundary if they want to think in millimetres.
"""

from __future__ import annotations

import math
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
    through the printer, so `width` is the label's long axis.
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


def text_size(text: str, font: ImageFont.FreeTypeFont) -> tuple[int, int]:
    bbox = font.getbbox(text)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def fit_text_to_height(
    text: str, height_dots: int, font_path: str | Path | None = None, max_size: int = 200
) -> ImageFont.FreeTypeFont:
    """Largest font that fits the text within `height_dots`, using binary search."""
    lo, hi = 6, max_size
    best = lo
    while lo <= hi:
        mid = (lo + hi) // 2
        font = load_font(font_path, mid)
        _, h = text_size(text, font)
        if h <= height_dots:
            best = mid
            lo = mid + 1
        else:
            hi = mid - 1
    return load_font(font_path, best)


def fit_text_to_box(
    text: str, box_w: int, box_h: int, font_path: str | Path | None = None, max_size: int = 200
) -> ImageFont.FreeTypeFont:
    """Largest font that fits the text within `box_w × box_h`."""
    lo, hi = 6, max_size
    best = lo
    while lo <= hi:
        mid = (lo + hi) // 2
        font = load_font(font_path, mid)
        w, h = text_size(text, font)
        if w <= box_w and h <= box_h:
            best = mid
            lo = mid + 1
        else:
            hi = mid - 1
    return load_font(font_path, best)


def draw_centered_text(
    canvas: LabelCanvas,
    text: str,
    font: ImageFont.FreeTypeFont,
    y: int | None = None,
    x: int | None = None,
) -> None:
    w, h = text_size(text, font)
    cx = (canvas.length_dots - w) // 2 if x is None else x
    cy = (canvas.height_dots - h) // 2 if y is None else y
    canvas.draw.text((cx, cy), text, fill="black", font=font)


def draw_dashed_vline(canvas: LabelCanvas, x: int, dash: int = 4, gap: int = 4) -> None:
    y = 0
    while y < canvas.height_dots:
        canvas.draw.line([(x, y), (x, min(y + dash, canvas.height_dots))], fill="black", width=1)
        y += dash + gap


def split_lines_to_fit(
    text: str, width_dots: int, font: ImageFont.FreeTypeFont
) -> list[str]:
    """Greedy word-wrap. Long words get truncated with '…'."""
    lines: list[str] = []
    words = text.split()
    line = ""
    for word in words:
        candidate = f"{line} {word}".strip()
        if text_size(candidate, font)[0] <= width_dots:
            line = candidate
        else:
            if line:
                lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines or [""]


def estimate_text_length_mm(text: str, height_dots: int, font_path: str | Path | None = None) -> float:
    """Quickly estimate the mm length needed to print `text` at height_dots tall."""
    font = fit_text_to_height(text, height_dots, font_path)
    w, _ = text_size(text, font)
    return dots_to_mm(w + math.ceil(height_dots * 0.3))  # + padding
