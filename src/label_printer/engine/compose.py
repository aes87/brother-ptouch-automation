"""Post-render decoration: append optional QR / bitmap to any rendered label.

Templates are responsible for the *body* of a label — whatever text, icons,
polarity markers, or layout that category needs. Cross-cutting additions
(a QR pointing at canonical context, an icon from an arbitrary image file,
etc.) live here so every template gets them for free.

The contract is simple: ``compose_extras(body, extras, tape)`` returns a
new image that is the body with the extras stacked on the right edge, each
separated by a small gap. Body height is preserved; the canvas length grows
to fit the additions.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from label_printer.engine.layout import mm_to_dots
from label_printer.engine.qr import render_qr
from label_printer.tape import TapeWidth, geometry_for

# Keys that compose_extras knows how to handle. A template that renders one
# of these internally (e.g. ``utility/qr``) declares so via
# ``Template.handles_extras``, and the caller strips those keys before
# composing — see ``strip_template_handled``.
EXTRA_KEYS = ("link", "image")


def strip_template_handled(extras: dict, template) -> dict:
    """Remove extras that the template already handles internally.

    Templates opt out of external composition for specific keys by setting
    the ``handles_extras`` class attribute (a frozenset of key names).
    Prevents double-rendering: ``utility/qr`` handles ``link`` itself, so
    external composition must not add a second QR.
    """
    handled = getattr(template, "handles_extras", frozenset())
    return {k: v for k, v in extras.items() if k not in handled}


def _load_and_fit_image(path: str | Path, target_h: int, threshold: int = 128) -> Image.Image:
    """Load an image file and scale it to exactly ``target_h`` pixels tall, 1-bit.

    Preserves aspect ratio, handles RGBA by flattening against white,
    thresholds to monochrome. Returned image is RGB so it can be pasted onto
    a ``LabelCanvas``.
    """
    src = Image.open(Path(str(path)).expanduser())
    if src.height == 0:
        raise ValueError(f"image has zero height: {path}")
    scale = target_h / src.height
    new_w = max(1, int(round(src.width * scale)))
    resized = src.resize((new_w, target_h), Image.Resampling.LANCZOS)
    if resized.mode == "RGBA":
        flat = Image.new("RGB", resized.size, (255, 255, 255))
        flat.paste(resized, mask=resized.split()[-1])
        resized = flat
    gray = resized.convert("L")
    return gray.point(lambda v: 0 if v < threshold else 255, mode="1").convert("RGB")


def compose_extras(body: Image.Image, extras: dict, tape: TapeWidth) -> Image.Image:
    """Append optional QR / bitmap extras to the right edge of ``body``.

    Known keys:
        link:  QR payload (short-form, URL, or opaque string). Rendered as a
               square QR sized to the full print height.
        image: Path to a bitmap. Fit to print height, preserving aspect.

    Unknown keys are ignored. Returns ``body`` unchanged if no extras apply.
    """
    link = extras.get("link")
    image = extras.get("image")
    if not link and not image:
        return body

    geom = geometry_for(tape)
    target_h = geom.print_pins

    additions: list[Image.Image] = []
    if link:
        additions.append(render_qr(str(link), target_h))
    if image:
        additions.append(_load_and_fit_image(image, target_h))

    gap = mm_to_dots(1.5)
    extras_w = sum(img.width for img in additions) + gap * len(additions)
    new_w = body.width + extras_w

    canvas = Image.new("RGB", (new_w, body.height), "white")
    canvas.paste(body, (0, 0))
    x = body.width + gap
    for img in additions:
        canvas.paste(img, (x, 0))
        x += img.width + gap
    return canvas
