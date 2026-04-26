"""Image preprocessing: orientation, monochrome conversion, sanity checks.

The printer consumes raster data column-by-column, where each column has
exactly 128 pins (bits). So the Pillow image we hand to the encoder must
be oriented so that:

- `image.height` == `geometry.print_pins` for the loaded tape
- `image.width`  == label length in dots (@180 DPI → `length_mm * 180 / 25.4`)

Users typically compose labels in "landscape" orientation (wide × short),
which matches this convention directly. If a template composes the label
in portrait orientation by accident, we rotate it 90° to fit.

Ink convention: in all input modes, DARKER pixels are "ink" (pin fires).
Mode '1' stores {0: black, 255: white} — black → ink.
Mode 'L' threshold is 128 — dark → ink.
RGBA transparent pixels are treated as background.
"""

from __future__ import annotations

from PIL import Image

from label_printer.constants import LINE_LENGTH_BYTES
from label_printer.tape import TapeGeometry, TapeWidth, geometry_for


class ImageFitError(ValueError):
    pass


_MONO_THRESHOLD = 128


def fit_to_tape(image: Image.Image, tape: TapeWidth) -> Image.Image:
    """Return an image whose height matches the printable pin count for `tape`.

    Accepts a landscape image already sized correctly, or rotates a portrait
    image 90° if its width matches. Anything else is an error — silent
    scaling would ruin typography at 180 DPI.
    """
    geom = geometry_for(tape)

    if image.height == geom.print_pins:
        return image
    if image.width == geom.print_pins:
        return image.transpose(Image.ROTATE_90)

    raise ImageFitError(
        f"Image does not fit tape {tape.name}: expected one dimension to be "
        f"{geom.print_pins} pins, got {image.width}×{image.height}."
    )


def to_monochrome(image: Image.Image) -> Image.Image:
    """Convert to 1-bit (mode '1'). Returns an image where black (0) == ink."""
    mode = image.mode

    if mode == "P":
        image = image.convert("RGBA") if "transparency" in image.info else image.convert("RGB")
        mode = image.mode

    if mode == "RGBA":
        # Flatten against white so transparency → background.
        bg = Image.new("RGB", image.size, (255, 255, 255))
        bg.paste(image, mask=image.split()[-1])
        image = bg
        mode = "RGB"

    if mode == "RGB":
        image = image.convert("L")
        mode = "L"

    if mode == "L":
        # ``point`` with mode='1' is a hard threshold — explicitly *not*
        # ``image.convert('1')``, which defaults to Floyd-Steinberg dithering
        # that scatters grey ink dots through text and ruins legibility on
        # small tape. Keep this as point()-with-threshold for text safety.
        return image.point(lambda x: 0 if x < _MONO_THRESHOLD else 255, mode="1")

    if mode == "1":
        return image

    raise ImageFitError(f"Unsupported image mode: {mode}")


def image_to_raster_bytes(image: Image.Image, tape: TapeWidth) -> bytes:
    """Flatten a fitted, monochrome image to the raw raster bitstream.

    Output is `image.width * LINE_LENGTH_BYTES` bytes — one 16-byte raster
    line per column of the image. Pin alignment is:

        [margin_pins zeros] [print_pins ink bits] [margin_pins zeros]

    MSB-first within each byte, matching the printer's convention.
    """
    fitted = fit_to_tape(image, tape)
    mono = to_monochrome(fitted)
    geom = geometry_for(tape)

    assert mono.height == geom.print_pins
    pixels = mono.load()

    out = bytearray()
    margin = geom.margin_pins
    for x in range(mono.width):
        bits = bytearray(LINE_LENGTH_BYTES)
        for y in range(mono.height):
            # mode '1': 0 = black = ink. Skip white pixels.
            if pixels[x, y]:
                continue
            pin = margin + y
            bits[pin // 8] |= 1 << (7 - (pin % 8))
        out.extend(bits)
    return bytes(out)


def geometry(tape: TapeWidth) -> TapeGeometry:
    """Convenience re-export."""
    return geometry_for(tape)
