"""CLI smoke tests."""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from label_printer.cli import main


def test_list():
    result = CliRunner().invoke(main, ["list"])
    assert result.exit_code == 0
    assert "kitchen/pantry_jar" in result.output
    assert "electronics/cable_flag" in result.output


def test_list_filter():
    result = CliRunner().invoke(main, ["list", "--category", "electronics"])
    assert result.exit_code == 0
    assert "electronics/cable_flag" in result.output
    assert "kitchen/pantry_jar" not in result.output


def test_show():
    result = CliRunner().invoke(main, ["show", "kitchen/pantry_jar"])
    assert result.exit_code == 0
    assert "purchased" in result.output


def test_render_template(tmp_path: Path):
    png_out = tmp_path / "pantry.png"
    bin_out = tmp_path / "pantry.bin"
    result = CliRunner().invoke(main, [
        "render", "kitchen/pantry_jar",
        "-f", "name=FLOUR",
        "-f", "purchased=2026-04-19",
        "--png-out", str(png_out),
        "--bin-out", str(bin_out),
    ])
    assert result.exit_code == 0, result.output
    assert png_out.exists()
    assert bin_out.exists()
    assert bin_out.stat().st_size > 200


def test_print_template_dryrun(tmp_path: Path):
    bin_out = tmp_path / "spice.bin"
    result = CliRunner().invoke(main, [
        "print", "kitchen/spice",
        "-f", "name=Paprika",
        "--bin-out", str(bin_out),
    ])
    assert result.exit_code == 0, result.output
    assert "dry-run" in result.output
    assert bin_out.exists()


def test_print_defaults_to_dry_run(tmp_path: Path):
    result = CliRunner().invoke(main, [
        "print", "kitchen/spice", "-f", "name=Paprika",
        "--bin-out", str(tmp_path / "dry.bin"),
    ])
    assert result.exit_code == 0, result.output
    assert "dry-run" in result.output
    assert (tmp_path / "dry.bin").exists()


def test_print_send_requires_a_configured_host(tmp_path: Path, monkeypatch):
    """Without a host (no flag, no env, no state), --send fails with a clear message."""
    monkeypatch.setenv("LABEL_PRINTER_CONFIG_DIR", str(tmp_path))
    monkeypatch.delenv("LABEL_PRINTER_HOST", raising=False)
    import importlib

    from label_printer import state as state_mod
    importlib.reload(state_mod)

    result = CliRunner().invoke(main, [
        "print", "kitchen/spice", "-f", "name=x", "--send",
    ])
    assert result.exit_code != 0
    assert "no printer host configured" in result.output


def test_print_send_rejects_unimplemented_transports(tmp_path: Path, monkeypatch):
    """USB / Bluetooth still raise the 'not available yet' error."""
    monkeypatch.setenv("LABEL_PRINTER_CONFIG_DIR", str(tmp_path))
    result = CliRunner().invoke(main, [
        "print", "kitchen/spice", "-f", "name=x", "--send", "--transport", "usb",
    ])
    assert result.exit_code != 0
    assert "not available yet" in result.output


def test_tape_persistence(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("LABEL_PRINTER_CONFIG_DIR", str(tmp_path))
    # force module reload so _STATE_FILE picks up the env
    import importlib

    from label_printer import state as state_mod
    importlib.reload(state_mod)

    result = CliRunner(env={"LABEL_PRINTER_CONFIG_DIR": str(tmp_path)}).invoke(main, ["tape", "24"])
    assert result.exit_code == 0, result.output
    state = state_mod.load()
    assert state.tape_mm == 24
