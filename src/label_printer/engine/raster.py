"""Brother raster command encoder.

Encodes a Pillow image into the exact byte stream accepted by the PT-P750W
(and its raster-compatible siblings, PT-P710BT and PT-E550W).
The output of `encode_job()` is ready to write to a transport (USB / BT /
dry-run) with no further processing.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

import packbits
from PIL import Image

from label_printer.constants import (
    CMD_ADVANCED_MODE_PREFIX,
    CMD_AUTOCUT_EVERY_PREFIX,
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


def _print_information(
    raster_data_len: int,
    tape: TapeWidth,
    *,
    starting_page: int = 0,
) -> bytes:
    """Build the ESC i z print-information command.

    Per Brother's reference: the `n4..n7` field is `raster_data_len >> 4`
    (i.e. the number of raster lines, given each line is 16 bytes).

    ``starting_page`` is the n9 byte: 0 = starting page (or only page),
    1 = middle page in a chain, 2 = last page in a chain. The PT-P750W
    relies on this byte to chain-print correctly with half-cuts.
    """
    lines = raster_data_len // LINE_LENGTH_BYTES
    return (
        CMD_PRINT_INFORMATION_PREFIX
        + b"\x84\x00"
        + int(tape).to_bytes(1, "little")
        + b"\x00"
        + lines.to_bytes(4, "little")
        + starting_page.to_bytes(1, "little")
        + b"\x00"
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
    """The single-label prologue. Used by :func:`encode_job` only.

    :func:`encode_batch` constructs its own job-level header inline because
    its structure is fundamentally different: control codes are emitted
    once at the start (not per page), auto-cut is forced off, and an extra
    ESC i K kick is sent before the last page. If you're adding a new
    job-level command, update both this function and ``encode_batch``.

    The ``ESC i A 01`` here declares "cut after every 1 label" — the
    standard single-label behavior. With auto-cut on (the single-label
    default), this is what the printer would assume anyway, but stating
    it explicitly makes the job self-contained against printer-side
    persistent overrides.
    """
    return (
        INVALIDATE_BYTES
        + CMD_INITIALIZE
        + CMD_DYNAMIC_MODE_RASTER
        + CMD_ENABLE_STATUS_NOTIFICATION
        + _print_information(raster_data_len, tape)
        + CMD_MODE_PREFIX + options.mode_flags().to_bytes(1, "little")
        + CMD_AUTOCUT_EVERY_PREFIX + b"\x01"
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

    The output is one strip held together by the liner with half-cuts
    between labels and a full feed-and-cut at the end.

    The structure follows the documented working pattern from three
    independent reference implementations (philpem/printer-driver-ptouch,
    boxine/rasterprynt, masatomizuta/py-brotherlabel):

    * Job-level control codes (``ESC i M / K / d``) are emitted **once**
      at the start, not per page. Auto-cut is forced **off** at the
      job level — when on, the printer full-cuts after every page
      regardless of the half-cut bit.
    * Per page: optional ``0x0C`` separator (between pages), per-page
      ``ESC i z`` with the ``n9`` byte indicating page position (0 =
      starting/only, 1 = middle, 2 = last), compression, raster data.
    * The terminating ``0x1A`` triggers the final feed-and-cut.

    Half-cuts between labels are produced by the half-cut bit in
    ``ESC i K`` (set once at job start), driven by the printer's page
    boundaries; the auto-cut bit must be off so the cutter doesn't fire
    on every page.

    Single-label batches degrade to a normal single-job encoding via
    :func:`encode_job` so byte-for-byte tests against single-job output
    keep working.
    """
    if not images:
        raise ValueError("encode_batch requires at least one image")
    options = options or RasterOptions()

    if len(images) == 1:
        return encode_job(images[0], tape, options)

    # Force auto-cut OFF on the job-level Mode byte: with auto-cut on, the
    # printer cuts after every page regardless of the half-cut / chain bits.
    # Force chaining ON (no-chain bit clear) so the printer doesn't terminate
    # mid-batch — the trailing 0x1A is what drives the final feed-and-cut.
    job_options = replace(options, auto_cut=False, chaining=True)
    # Last-page variant of ESC i K: chaining=False flips the no-chain bit on
    # so the terminating 0x1A produces a real feed-and-cut. With auto-cut off
    # at the job level, 0x1A alone only feeds — per spec, the no-chain bit
    # is what fires the end-of-job cut.
    kick_options = replace(job_options, chaining=False)

    out = bytearray()
    # Job-level prologue, sent ONCE.
    out += INVALIDATE_BYTES
    out += CMD_INITIALIZE
    out += CMD_DYNAMIC_MODE_RASTER
    out += CMD_ENABLE_STATUS_NOTIFICATION
    out += CMD_MODE_PREFIX + job_options.mode_flags().to_bytes(1, "little")
    out += CMD_ADVANCED_MODE_PREFIX + job_options.advanced_flags().to_bytes(1, "little")
    out += CMD_MARGIN_PREFIX + job_options.feed_dots.to_bytes(2, "little")

    last = len(images) - 1
    for i, image in enumerate(images):
        if i > 0:
            out += CMD_PRINT_NEXT_PAGE  # 0x0C between pages
        if i == last:
            # Re-emit ESC i K with the last-page variant before the final page.
            out += CMD_ADVANCED_MODE_PREFIX + kick_options.advanced_flags().to_bytes(1, "little")
        raster = image_to_raster_bytes(image, tape)
        # n9 = 0 for the first/only page, 1 for middle pages, 2 for the last.
        n9 = 2 if i == last else (0 if i == 0 else 1)
        out += _print_information(len(raster), tape, starting_page=n9)
        out += CMD_COMPRESSION_TIFF
        out += _encode_raster_lines(raster)

    out += CMD_PRINT_AND_FEED  # 0x1A — final feed and cut
    return bytes(out)
