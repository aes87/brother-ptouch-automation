"""Brother raster command encoder.

Encodes a Pillow image into the exact byte stream accepted by a PT-P710BT.
The output of `encode_job()` is ready to write to a transport (USB / BT /
dry-run) with no further processing.
"""

from __future__ import annotations

from dataclasses import dataclass

import packbits
from PIL import Image

from label_printer.constants import (
    CMD_ADVANCED_MODE_PREFIX,
    CMD_COMPRESSION_TIFF,
    CMD_DYNAMIC_MODE_RASTER,
    CMD_ENABLE_STATUS_NOTIFICATION,
    CMD_INITIALIZE,
    CMD_MARGIN_PREFIX,
    CMD_MODE_PREFIX,
    CMD_PRINT_AND_FEED,
    CMD_PRINT_INFORMATION_PREFIX,
    CMD_PRINT_NEXT_PAGE,
    CMD_RASTER_LINE,
    CMD_RASTER_ZERO_LINE,
    DEFAULT_FEED_DOTS,
    INVALIDATE_BYTES,
    LINE_LENGTH_BYTES,
    Mode,
)
from label_printer.engine.image import image_to_raster_bytes
from label_printer.tape import TapeWidth


@dataclass(frozen=True)
class RasterOptions:
    """Options that control the print command stream.

    ``half_cut`` is supported by the PT-P750W (and PT-E550W). The PT-P710BT
    accepts the bit without error but silently ignores it on hardware that
    lacks the physical mechanism. Leave enabled — harmless if unsupported.
    """

    auto_cut: bool = True
    mirror: bool = False
    chaining: bool = False
    half_cut: bool = True
    feed_dots: int = DEFAULT_FEED_DOTS

    def mode_flags(self) -> int:
        flags = 0
        if self.auto_cut:
            flags |= Mode.AUTO_CUT
        if self.mirror:
            flags |= Mode.MIRROR_PRINTING
        return flags

    def advanced_flags(self) -> int:
        # Brother "Set expanded mode" byte (ESC i K):
        #   bit 2 (0x04) = half-cut (leaves the liner intact between labels)
        #   bit 3 (0x08) = no chain printing (feed + cut after last page)
        flags = 0x00
        if self.half_cut:
            flags |= 0x04
        if not self.chaining:
            flags |= 0x08
        return flags


def _print_information(raster_data_len: int, tape: TapeWidth) -> bytes:
    """Build the ESC i z print-information command.

    Per Brother's reference: the `n4..n7` field is `raster_data_len >> 4`
    (i.e. the number of raster lines, given each line is 16 bytes).
    """
    lines = raster_data_len // LINE_LENGTH_BYTES
    return (
        CMD_PRINT_INFORMATION_PREFIX
        + b"\x84\x00"
        + int(tape).to_bytes(1, "little")
        + b"\x00"
        + lines.to_bytes(4, "little")
        + b"\x00\x00"
    )


def _encode_raster_lines(raster: bytes) -> bytes:
    """TIFF-PackBits-encode each 16-byte line, using the Z shortcut for zeros."""
    buf = bytearray()
    for i in range(0, len(raster), LINE_LENGTH_BYTES):
        line = raster[i : i + LINE_LENGTH_BYTES]
        if line == b"\x00" * LINE_LENGTH_BYTES:
            buf += CMD_RASTER_ZERO_LINE
        else:
            packed = packbits.encode(line)
            buf += CMD_RASTER_LINE
            buf += len(packed).to_bytes(2, "little")
            buf += packed
    return bytes(buf)


def build_prologue(raster_data_len: int, tape: TapeWidth, options: RasterOptions) -> bytes:
    """Everything that comes before the raster data in a print job."""
    return (
        INVALIDATE_BYTES
        + CMD_INITIALIZE
        + CMD_DYNAMIC_MODE_RASTER
        + CMD_ENABLE_STATUS_NOTIFICATION
        + _print_information(raster_data_len, tape)
        + CMD_MODE_PREFIX + options.mode_flags().to_bytes(1, "little")
        + CMD_ADVANCED_MODE_PREFIX + options.advanced_flags().to_bytes(1, "little")
        + CMD_MARGIN_PREFIX + options.feed_dots.to_bytes(2, "little")
        + CMD_COMPRESSION_TIFF
    )


def encode_job(
    image: Image.Image,
    tape: TapeWidth,
    options: RasterOptions | None = None,
) -> bytes:
    """Encode a full print job for one label.

    Returns the complete byte stream — initialization, control codes, raster
    data, and print-and-feed terminator — ready to hand to a Transport.
    """
    options = options or RasterOptions()
    raster = image_to_raster_bytes(image, tape)
    return encode_job_from_raster(raster, tape, options)


def encode_job_from_raster(
    raster: bytes,
    tape: TapeWidth,
    options: RasterOptions | None = None,
) -> bytes:
    """Low-level entry: already-flattened raster bytes → full command stream.

    Useful for tests that want to validate the command framing independently
    of image interpretation, and for upstream pipelines that rasterise
    somewhere else.
    """
    options = options or RasterOptions()
    prologue = build_prologue(len(raster), tape, options)
    return prologue + _encode_raster_lines(raster) + CMD_PRINT_AND_FEED


def encode_batch(
    images: list[Image.Image],
    tape: TapeWidth,
    options: RasterOptions | None = None,
) -> bytes:
    """Encode multiple labels into one chained print job.

    With the default ``options`` (``half_cut=True``, ``auto_cut=True``), the
    printer produces a partial cut between each label — they come off the
    printer as a single strip attached by the liner, which is easier to
    handle than N separate strips. The final label gets a full feed-and-cut.

    Pages are framed with per-page ``print_information`` + control codes,
    separated by ``0x0C`` (next page) and terminated by ``0x1A`` (print and
    feed). The session-level ``invalidate`` + ``ESC @`` + dynamic-mode +
    status-notification commands are emitted once at the start.
    """
    if not images:
        raise ValueError("encode_batch requires at least one image")
    options = options or RasterOptions()

    out = bytearray()
    out += INVALIDATE_BYTES
    out += CMD_INITIALIZE
    out += CMD_DYNAMIC_MODE_RASTER
    out += CMD_ENABLE_STATUS_NOTIFICATION

    last = len(images) - 1
    for i, image in enumerate(images):
        raster = image_to_raster_bytes(image, tape)
        # Per-page declaration: the raster-line count in print_information
        # is specific to this page.
        out += _print_information(len(raster), tape)
        out += CMD_MODE_PREFIX + options.mode_flags().to_bytes(1, "little")
        out += CMD_ADVANCED_MODE_PREFIX + options.advanced_flags().to_bytes(1, "little")
        out += CMD_MARGIN_PREFIX + options.feed_dots.to_bytes(2, "little")
        out += CMD_COMPRESSION_TIFF
        out += _encode_raster_lines(raster)
        out += CMD_PRINT_AND_FEED if i == last else CMD_PRINT_NEXT_PAGE

    return bytes(out)
