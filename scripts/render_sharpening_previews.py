"""Render the three torture-test sharpening previews.

Produces, for each template, a *_before.png (rendered against main),
*_after.png (rendered against the current worktree), and *_compare.png
(both stacked at 4x with labels). When invoked with --after-only it
skips the "before" pass and only rebuilds the after + compare panels —
useful when iterating on the after side without re-checking out main.

The three templates are picked to stress different parts of the pipeline:

* kitchen/pantry_jar — bold headline + tiny date subtitle (Spleen regime)
* kitchen/spice — three-part subtitle, joins
* electronics/cable_flag — wraps a small-print block under a big headline,
  per-face QR/image, dashed fold lines

Usage::

    python scripts/render_sharpening_previews.py --after-only
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from label_printer.engine.layout import render_two_line_label
from label_printer.tape import TapeWidth
from label_printer.templates.electronics.cable_flag import CableFlagTemplate

OUT = Path(__file__).resolve().parents[1] / "docs" / "previews" / "sharpening"

SCALE = 4
SIDE_PAD = 16
LABEL_GAP = 32
LABEL_BAR = 30


def _render_pantry_jar() -> Image.Image:
    return render_two_line_label(
        TapeWidth.MM_12,
        "AP Flour",
        "2026-04-19 · exp 2027-04-19",
        padding_mm=2.0,
    )


def _render_spice() -> Image.Image:
    return render_two_line_label(
        TapeWidth.MM_12,
        "Smoked Paprika",
        "Spain · bb 2027-01",
        padding_mm=2.0,
    )


def _render_cable_flag() -> Image.Image:
    tmpl = CableFlagTemplate()
    return tmpl.render(
        {
            "source": "NAS",
            "dest": "SWITCH p3",
            "date": "2026-04-25",
            "details": "VLAN 20",
            "wire": "ethernet",
        },
        TapeWidth.MM_12,
    )


TEMPLATES = {
    "kitchen_pantry_jar": _render_pantry_jar,
    "kitchen_spice": _render_spice,
    "electronics_cable_flag": _render_cable_flag,
}


def _scale(img: Image.Image, factor: int = SCALE) -> Image.Image:
    return img.resize((img.width * factor, img.height * factor), Image.NEAREST)


def _label_bar(text: str, width: int, height: int) -> Image.Image:
    bar = Image.new("RGB", (width, height), "white")
    d = ImageDraw.Draw(bar)
    try:
        font = ImageFont.truetype(
            str(Path(__file__).resolve().parents[1] / "assets" / "fonts" / "DejaVuSans-Bold.ttf"),
            size=16,
        )
    except OSError:
        font = ImageFont.load_default()
    d.text((SIDE_PAD, height // 2), text, fill="black", anchor="lm", font=font)
    return bar


def _compare(before: Image.Image, after: Image.Image) -> Image.Image:
    width = max(before.width, after.width) * SCALE + SIDE_PAD * 2
    row_h = before.height * SCALE
    height = LABEL_BAR + row_h + LABEL_BAR + row_h + LABEL_GAP // 2
    canvas = Image.new("RGB", (width, height), "white")
    y = 0
    canvas.paste(_label_bar("BEFORE", width, LABEL_BAR), (0, y))
    y += LABEL_BAR
    canvas.paste(_scale(before), (SIDE_PAD, y))
    y += row_h
    canvas.paste(_label_bar("AFTER", width, LABEL_BAR), (0, y))
    y += LABEL_BAR
    canvas.paste(_scale(after), (SIDE_PAD, y))
    return canvas


def render_after_only() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, fn in TEMPLATES.items():
        after = fn()
        after.save(OUT / f"{name}_after.png")
        before = Image.open(OUT / f"{name}_before.png")
        # Pad the shorter image to match width so comparison is honest.
        max_w = max(before.width, after.width)
        if before.width < max_w:
            padded = Image.new("RGB", (max_w, before.height), "white")
            padded.paste(before, (0, 0))
            before = padded
        if after.width < max_w:
            padded = Image.new("RGB", (max_w, after.height), "white")
            padded.paste(after, (0, 0))
            after = padded
        _compare(before, after).save(OUT / f"{name}_compare.png")
        print(f"wrote {name}_after.png ({after.size}) + {name}_compare.png")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--after-only", action="store_true",
                        help="Only rebuild *_after.png + *_compare.png (assumes "
                             "*_before.png already on disk).")
    args = parser.parse_args()
    if not args.after_only:
        raise SystemExit("Full BEFORE/AFTER regen not implemented in this script — "
                         "the before images are pinned from main, edit and re-run "
                         "with --after-only after each iteration.")
    render_after_only()


if __name__ == "__main__":
    main()
