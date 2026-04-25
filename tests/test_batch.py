"""Multi-label batch encoding with half-cut between pages."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner
from PIL import Image

from label_printer import RasterOptions, TapeWidth, encode_batch, encode_job
from label_printer.cli import main
from label_printer.constants import CMD_PRINT_AND_FEED
from label_printer.tape import geometry_for


def _test_image(tape: TapeWidth, length: int = 40) -> Image.Image:
    return Image.new("1", (length, geometry_for(tape).print_pins), 1)


def test_batch_of_one_degrades_to_single_job():
    """A 1-image batch is byte-for-byte identical to encode_job — different
    control structures (auto-cut on for single, off for batch) need single-
    label paths to behave normally."""
    tape = TapeWidth.MM_12
    img = _test_image(tape)
    single = encode_job(img, tape)
    batched = encode_batch([img], tape)
    assert single == batched


def test_batch_rejects_empty():
    with pytest.raises(ValueError, match="at least one"):
        encode_batch([], TapeWidth.MM_12)


def test_batch_emits_one_set_of_control_codes_plus_terminating_kick():
    """ESC i M / d are job-level — emit once. ESC i K appears twice: once
    at the job-level prologue (chain on, half-cut on) and once right before
    the last page (no-chain on) so the terminating 0x1A produces a real cut.
    Per philpem / rasterprynt / py-brotherlabel."""
    tape = TapeWidth.MM_12
    data = encode_batch([_test_image(tape)] * 3, tape)
    assert data.count(b"\x1b\x69\x4d") == 1, "ESC i M (Mode) must appear once"
    assert data.count(b"\x1b\x69\x64") == 1, "ESC i d (Margin) must appear once"
    # ESC i K appears at job start AND before the final page.
    assert data.count(b"\x1b\x69\x4b") == 2
    # ESC i A must NOT appear — auto-cut is off at the job level, so
    # cut-every-N is meaningless. A regression introducing it (e.g. an
    # encode_batch refactor that calls build_prologue) is exactly what
    # this assertion guards against.
    assert data.count(b"\x1b\x69\x41") == 0, "ESC i A must not appear in batch output"
    # Three ESC i z (one per page) and the final terminator.
    assert data.count(b"\x1b\x69\x7a") == 3
    assert data.endswith(CMD_PRINT_AND_FEED)


def test_batch_advanced_mode_starts_chain_on_then_flips_for_last_page():
    """Job-level ESC i K = 0x04 (half-cut, chain on). The second ESC i K
    just before the last page = 0x0C (half-cut + no-chain) so the
    terminating 0x1A fires a feed-and-cut."""
    tape = TapeWidth.MM_12
    data = encode_batch([_test_image(tape)] * 3, tape)
    positions = []
    pos = 0
    while True:
        idx = data.find(b"\x1b\x69\x4b", pos)
        if idx < 0:
            break
        positions.append(data[idx + 3])
        pos = idx + 4
    assert positions == [0x04, 0x0C]


def test_batch_disables_auto_cut_at_job_level():
    """The single Mode byte must have auto-cut bit (0x40) cleared. With
    auto-cut on, the printer full-cuts every page regardless of half-cut
    bit — the documented Brother failure mode for batch + half-cut."""
    tape = TapeWidth.MM_12
    data = encode_batch([_test_image(tape)] * 2, tape)
    idx = data.find(b"\x1b\x69\x4d")
    assert idx >= 0
    mode_byte = data[idx + 3]
    assert mode_byte & 0x40 == 0, f"auto-cut must be off in batch mode, got 0x{mode_byte:02x}"


def test_batch_per_page_n9_indicates_position():
    """ESC i z's n9 byte (offset +11 from the prefix start) per-page marks
    starting page (0), middle pages (1), and last page (2)."""
    tape = TapeWidth.MM_12
    data = encode_batch([_test_image(tape, 20)] * 3, tape)
    n9_values = []
    pos = 0
    while True:
        idx = data.find(b"\x1b\x69\x7a", pos)
        if idx < 0:
            break
        # ESC i z (3) + n1..n8 (8) = 11; n9 sits at offset +11.
        n9_values.append(data[idx + 11])
        pos = idx + 13
    assert n9_values == [0, 1, 2]


def test_batch_no_half_cut_flag_clears_half_cut_bit():
    """With half_cut=False the job-level ESC i K drops the half-cut bit;
    the pre-last kick still flips no-chain on for the terminating cut."""
    tape = TapeWidth.MM_12
    data = encode_batch(
        [_test_image(tape)] * 2, tape, RasterOptions(half_cut=False)
    )
    positions = []
    pos = 0
    while True:
        idx = data.find(b"\x1b\x69\x4b", pos)
        if idx < 0:
            break
        positions.append(data[idx + 3])
        pos = idx + 4
    assert positions == [0x00, 0x08]  # no half-cut + chain on, then no-chain


def test_batch_has_single_session_prologue():
    tape = TapeWidth.MM_12
    data = encode_batch([_test_image(tape)] * 3, tape)
    # Invalidate + initialize happen once at the very start of the job.
    assert data[:100] == b"\x00" * 100
    assert data[100:102] == b"\x1b\x40"
    # Dynamic-mode and status-notify only appear once.
    assert data.count(b"\x1b\x69\x61\x01") == 1
    assert data.count(b"\x1b\x69\x21\x00") == 1
    # ESC i z print-information appears once per page.
    assert data.count(b"\x1b\x69\x7a") == 3


# --- CLI `lp batch` ---------------------------------------------------------

def test_cli_batch_dry_run(tmp_path: Path):
    spec = [
        {"template": "kitchen/spice", "tape_mm": 12,
         "fields": {"name": "Paprika"}},
        {"template": "kitchen/spice", "tape_mm": 12,
         "fields": {"name": "Cumin"}},
        {"template": "kitchen/spice", "tape_mm": 12,
         "fields": {"name": "Oregano"}},
    ]
    spec_path = tmp_path / "batch.json"
    spec_path.write_text(json.dumps(spec))
    out = tmp_path / "out.bin"
    result = CliRunner().invoke(
        main, ["batch", str(spec_path), "--bin-out", str(out)]
    )
    assert result.exit_code == 0, result.output
    assert "batched 3 label" in result.output
    assert "dry-run" in result.output
    assert out.exists()
    data = out.read_bytes()
    # Three pages → three print-information commands; one final 0x1A.
    assert data.count(b"\x1b\x69\x7a") == 3
    assert data.endswith(CMD_PRINT_AND_FEED)


def test_cli_batch_rejects_mixed_tape(tmp_path: Path):
    spec = [
        {"template": "kitchen/spice", "tape_mm": 12, "fields": {"name": "a"}},
        {"template": "kitchen/spice", "tape_mm": 24, "fields": {"name": "b"}},
    ]
    spec_path = tmp_path / "batch.json"
    spec_path.write_text(json.dumps(spec))
    result = CliRunner().invoke(main, ["batch", str(spec_path)])
    assert result.exit_code != 0
    assert "tape width" in result.output.lower()


def test_cli_batch_send_requires_configured_host(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("LABEL_PRINTER_CONFIG_DIR", str(tmp_path))
    monkeypatch.delenv("LABEL_PRINTER_HOST", raising=False)
    import importlib

    from label_printer import state as state_mod
    importlib.reload(state_mod)

    spec = [{"template": "kitchen/spice", "tape_mm": 12, "fields": {"name": "x"}}]
    spec_path = tmp_path / "batch.json"
    spec_path.write_text(json.dumps(spec))
    result = CliRunner().invoke(main, ["batch", str(spec_path), "--send"])
    assert result.exit_code != 0
    assert "no printer host configured" in result.output
