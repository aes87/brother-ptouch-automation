"""Byte goldens for the raster encoder + cross-check against brother_pt."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from PIL import Image

from label_printer import RasterOptions, TapeWidth, encode_job, encode_job_from_raster
from label_printer.engine.image import image_to_raster_bytes, to_monochrome
from label_printer.engine.raster import _encode_raster_lines, build_prologue
from label_printer.tape import geometry_for
from tests.conftest import make_hello_image

GOLDEN_BIN_DIR = Path(__file__).parent / "golden" / "raster"
REGEN = "REGEN_GOLDENS" in os.environ


# --- Prologue framing --------------------------------------------------------

def test_prologue_is_deterministic():
    raster_len = 16 * 100
    prologue = build_prologue(raster_len, TapeWidth.MM_12, RasterOptions())
    assert prologue[:100] == b"\x00" * 100
    assert prologue[100:102] == b"\x1b\x40"
    assert prologue[102:106] == b"\x1b\x69\x61\x01"
    assert prologue[106:110] == b"\x1b\x69\x21\x00"
    assert prologue[110:113] == b"\x1b\x69\x7a"
    assert prologue[113] == 0x84
    assert prologue[115] == 12
    assert int.from_bytes(prologue[117:121], "little") == 100
    # ESC i A 01 (cut-every-N=1) sits between ESC i M and ESC i K. Verify it's
    # present, has the expected argument, and is positioned mid-bracket.
    mode_at = prologue.find(b"\x1b\x69\x4d")
    autocut_at = prologue.find(b"\x1b\x69\x41")
    advanced_at = prologue.find(b"\x1b\x69\x4b")
    assert autocut_at >= 0, "ESC i A missing from single-label prologue"
    assert prologue[autocut_at + 3] == 0x01, "ESC i A arg should be 1 for single-label"
    assert mode_at < autocut_at < advanced_at


def test_raster_lines_use_zero_shortcut_for_blank_rows():
    encoded = _encode_raster_lines(b"\x00" * 16 * 3)
    assert encoded == b"\x5a\x5a\x5a"


def test_raster_lines_tiff_packbits_for_nonblank():
    encoded = _encode_raster_lines(b"\xff" * 16)
    assert encoded[0:1] == b"\x47"
    length = int.from_bytes(encoded[1:3], "little")
    assert len(encoded) == 3 + length


def test_half_cut_bit_in_advanced_mode():
    # half_cut=True (default) sets bit 2 (0x04); chaining off sets bit 3 (0x08).
    prologue = build_prologue(16 * 4, TapeWidth.MM_12, RasterOptions())
    # Find the "ESC i K <flags>" sequence — 4 bytes: 1B 69 4B XX
    for i in range(len(prologue) - 4):
        if prologue[i : i + 3] == b"\x1b\x69\x4b":
            assert prologue[i + 3] == 0x0C, "expected half-cut (0x04) + no-chain (0x08)"
            break
    else:
        raise AssertionError("advanced-mode command not found in prologue")


def test_half_cut_disabled():
    prologue = build_prologue(16 * 4, TapeWidth.MM_12, RasterOptions(half_cut=False))
    for i in range(len(prologue) - 4):
        if prologue[i : i + 3] == b"\x1b\x69\x4b":
            assert prologue[i + 3] == 0x08, "expected no-chain only, no half-cut"
            break
    else:
        raise AssertionError("advanced-mode command not found in prologue")


def test_full_job_terminates_with_print_and_feed():
    geom = geometry_for(TapeWidth.MM_12)
    img = make_hello_image(40, geom.print_pins)
    data = encode_job(img, TapeWidth.MM_12)
    assert data.endswith(b"\x1a")


# --- Image interpretation ---------------------------------------------------

def test_mode_L_dark_pixels_become_ink():
    """Dark 'L' pixels must set ink bits; light pixels must not."""
    tape = TapeWidth.MM_12
    geom = geometry_for(tape)
    img = Image.new("L", (4, geom.print_pins), 255)  # all white (bg)
    for y in range(geom.print_pins):
        img.putpixel((0, y), 0)  # black column 0 = full ink
    raster = image_to_raster_bytes(img, tape)

    # Column 0: ink rows should produce set bits in the middle pin band.
    col0 = raster[0:16]
    for pin in range(geom.margin_pins, geom.margin_pins + geom.print_pins):
        byte = col0[pin // 8]
        assert (byte >> (7 - pin % 8)) & 1 == 1, f"col0 pin {pin} should be ink"
    # Column 1: fully white, should be all zeros.
    assert raster[16:32] == b"\x00" * 16


def test_mode_1_black_pixels_become_ink():
    tape = TapeWidth.MM_12
    geom = geometry_for(tape)
    img = Image.new("1", (2, geom.print_pins), 1)  # all white
    for y in range(geom.print_pins):
        img.putpixel((0, y), 0)  # black col
    raster = image_to_raster_bytes(img, tape)
    assert raster[16:32] == b"\x00" * 16
    # Col 0 has ink in middle
    col0 = raster[0:16]
    assert col0 != b"\x00" * 16


def test_rgba_transparent_becomes_background():
    tape = TapeWidth.MM_12
    geom = geometry_for(tape)
    img = Image.new("RGBA", (4, geom.print_pins), (0, 0, 0, 0))  # transparent black
    raster = image_to_raster_bytes(img, tape)
    assert raster == b"\x00" * 16 * 4


def test_to_monochrome_rejects_weird_mode():
    img = Image.new("CMYK", (4, 4))
    with pytest.raises(Exception):  # noqa: B017
        to_monochrome(img)


# --- Pin alignment ----------------------------------------------------------

def test_margin_padding_respects_tape():
    """12mm tape uses only pins 29..98; pins 0..28 and 99..127 must be zero."""
    tape = TapeWidth.MM_12
    geom = geometry_for(tape)
    img = Image.new("1", (4, geom.print_pins), 0)  # fully black = fully ink
    raster = image_to_raster_bytes(img, tape)
    for col in range(4):
        line = raster[col * 16 : (col + 1) * 16]
        for pin in range(geom.margin_pins):
            byte = line[pin // 8]
            assert (byte >> (7 - pin % 8)) & 1 == 0, f"leading margin pin {pin}"
        for pin in range(geom.margin_pins, geom.margin_pins + geom.print_pins):
            byte = line[pin // 8]
            assert (byte >> (7 - pin % 8)) & 1 == 1, f"print pin {pin}"
        for pin in range(geom.margin_pins + geom.print_pins, 128):
            byte = line[pin // 8]
            assert (byte >> (7 - pin % 8)) & 1 == 0, f"trailing margin pin {pin}"


@pytest.mark.parametrize("tape,length", [(TapeWidth.MM_12, 32), (TapeWidth.MM_24, 64)])
def test_image_fits_tape(tape: TapeWidth, length: int):
    geom = geometry_for(tape)
    img = make_hello_image(length, geom.print_pins)
    raster = image_to_raster_bytes(img, tape)
    assert len(raster) == length * 16


# --- Cross-check against brother_pt at the raster-bytes layer ----------------
# The two libraries differ on how mode '1' is interpreted as ink (brother_pt
# treats white as ink for mode '1' inputs), so we check at the level where
# conventions unambiguously agree: identical raster bytes → identical output.

brother_pt = pytest.importorskip("brother_pt.cmd")


def _brother_pt_expected_bytes(raster: bytes, tape: TapeWidth, feed_dots: int) -> bytes:
    from brother_pt.cmd import (
        enable_status_notification,
        enter_dynamic_command_mode,
        gen_raster_commands,
        initialize,
        invalidate,
        margin_amount,
        print_information,
        print_with_feeding,
        set_advanced_mode,
        set_compression_mode,
        set_mode,
    )

    out = b""
    out += invalidate()
    out += initialize()
    out += enter_dynamic_command_mode()
    out += enable_status_notification()
    out += print_information(raster, int(tape))
    out += set_mode()
    out += set_advanced_mode()
    out += margin_amount(feed_dots)
    out += set_compression_mode()
    for cmd in gen_raster_commands(raster):
        out += cmd
    out += print_with_feeding()
    return out


def _strip_autocut_command(data: bytes) -> bytes:
    """Drop our ESC i A nn (4 bytes) so output can be compared against
    encoders that don't emit it — namely brother_pt's reference."""
    idx = data.find(b"\x1B\x69\x41")
    return data if idx < 0 else data[:idx] + data[idx + 4 :]


@pytest.mark.parametrize("tape", [TapeWidth.MM_12, TapeWidth.MM_24])
def test_matches_brother_pt_byte_for_byte(tape: TapeWidth):
    """Fixed raster bytes → identical command stream.

    brother_pt's reference encoder emits advanced-mode=0x08 (chaining off, no
    half-cut) and does NOT send ESC i A — its prologue assumes the printer's
    default cut-every-N. We send ESC i A explicitly so cut-every behavior is
    self-contained, so we strip it before comparing. The rest of the stream
    must still match byte-for-byte.
    """
    raster = bytes(
        # 4 lines, varied content to exercise Z-shortcut + packbits branches
        list(b"\x00" * 16)
        + list(b"\xff" * 16)
        + list(b"\xaa" * 16)
        + list(b"\x00" * 16)
    )
    ours = encode_job_from_raster(raster, tape, RasterOptions(feed_dots=0, half_cut=False))
    theirs = _brother_pt_expected_bytes(raster, tape, feed_dots=0)
    assert _strip_autocut_command(ours) == theirs, (
        f"byte mismatch (len ours={len(ours)}, theirs={len(theirs)})\n"
        f"first diff at byte "
        f"{next((i for i,(a,b) in enumerate(zip(_strip_autocut_command(ours), theirs, strict=False)) if a!=b), 'end')}"
    )


# --- Regenerable byte goldens -----------------------------------------------

@pytest.mark.parametrize("tape", [TapeWidth.MM_12, TapeWidth.MM_24])
def test_golden_hello(tape: TapeWidth):
    """Byte goldens — pinned to half_cut=False to keep in lockstep with brother_pt."""
    GOLDEN_BIN_DIR.mkdir(parents=True, exist_ok=True)
    geom = geometry_for(tape)
    img = make_hello_image(60, geom.print_pins)
    data = encode_job(img, tape, RasterOptions(feed_dots=0, half_cut=False))
    golden = GOLDEN_BIN_DIR / f"hello_{int(tape)}mm.bin"
    if REGEN or not golden.exists():
        golden.write_bytes(data)
    assert data == golden.read_bytes()
