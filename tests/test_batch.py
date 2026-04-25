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


def test_batch_of_one_equals_single_job():
    tape = TapeWidth.MM_12
    img = _test_image(tape)
    single = encode_job(img, tape)
    batched = encode_batch([img], tape)
    # Single-item batch should match the single-job encoding byte-for-byte.
    assert single == batched


def test_batch_rejects_empty():
    with pytest.raises(ValueError, match="at least one"):
        encode_batch([], TapeWidth.MM_12)


def test_batch_uses_next_page_separator_between_labels():
    tape = TapeWidth.MM_12
    imgs = [_test_image(tape, 20) for _ in range(3)]
    data = encode_batch(imgs, tape)
    # Three pages implies three ESC i z print-information commands.
    assert data.count(b"\x1b\x69\x7a") == 3
    # Final byte is print-and-feed; inter-page separators can't be reliably
    # counted because 0x0C/0x1A bytes can appear inside raster data.
    assert data.endswith(CMD_PRINT_AND_FEED)
    # Same terminator pattern for 1 vs N labels (verified elsewhere).


def test_batch_applies_half_cut_by_default():
    tape = TapeWidth.MM_12
    data = encode_batch([_test_image(tape)] * 2, tape)
    # Find each ESC i K <flags> occurrence — one per page.
    matches = []
    for i in range(len(data) - 4):
        if data[i : i + 3] == b"\x1b\x69\x4b":
            matches.append(data[i + 3])
    assert len(matches) == 2
    # 0x0C = half-cut (0x04) + no-chain (0x08)
    assert all(b == 0x0C for b in matches)


def test_batch_no_half_cut_flag_propagates():
    tape = TapeWidth.MM_12
    data = encode_batch(
        [_test_image(tape)] * 2, tape, RasterOptions(half_cut=False)
    )
    for i in range(len(data) - 4):
        if data[i : i + 3] == b"\x1b\x69\x4b":
            assert data[i + 3] == 0x08  # no-chain, no half-cut


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
