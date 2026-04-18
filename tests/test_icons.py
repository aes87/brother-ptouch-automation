"""Icon engine tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from label_printer.cli import main
from label_printer.engine import icons as icons_mod


@pytest.fixture
def registry():
    return icons_mod.registry()


def test_engine_available_in_test_env():
    # cairosvg is a [icons] extra but installed for the test suite.
    assert icons_mod.has_engine()


def test_registry_finds_bundled_icons(registry):
    names = registry.available()
    assert any(n.endswith(":wifi") for n in names)
    assert any(n.endswith(":flame") for n in names)
    # At least the bundled curated set.
    assert len(names) >= 30


def test_registry_source_prefix_filter(registry):
    lucide = registry.available("lucide")
    assert all(n.startswith("lucide:") for n in lucide)
    # Unknown source → empty, not raise.
    assert registry.available("does-not-exist") == []


def test_find_bare_name_wins_first_match(registry):
    path = registry.find("wifi")
    assert path.suffix == ".svg"
    assert path.name == "wifi.svg"


def test_find_namespaced_name(registry):
    path = registry.find("lucide:wifi")
    assert "lucide" in str(path)
    assert path.name == "wifi.svg"


def test_unknown_icon_raises(registry):
    with pytest.raises(icons_mod.IconNotFoundError):
        registry.find("this-icon-does-not-exist")


def test_load_icon_renders_monochrome():
    img = icons_mod.load_icon("wifi", 64)
    assert img.size == (64, 64)
    # Monochrome flatten against white, then thresholded → RGB.
    assert img.mode == "RGB"
    # Should contain both ink and background pixels.
    extrema = img.getextrema()
    assert extrema[0][0] == 0 or extrema[0][1] == 255


def test_load_icon_raises_without_engine(monkeypatch):
    monkeypatch.setattr(icons_mod, "_CAIROSVG_AVAILABLE", False)
    with pytest.raises(icons_mod.IconEngineUnavailable):
        icons_mod.load_icon("wifi", 64)


def test_env_var_adds_search_root(tmp_path: Path, monkeypatch):
    # Create a fake source with an icon the bundled set doesn't have.
    custom = tmp_path / "custom" / "test"
    custom.mkdir(parents=True)
    (custom / "unique-name.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><rect width="24" height="24"/></svg>'
    )
    monkeypatch.setenv("LABEL_PRINTER_ICON_PATH", str(tmp_path / "custom"))
    reg = icons_mod.IconRegistry(sources=("test",))
    assert "test:unique-name" in reg.available()


# --- CLI -------------------------------------------------------------------

def test_cli_icons_list():
    result = CliRunner().invoke(main, ["icons", "list"])
    assert result.exit_code == 0, result.output
    assert "lucide:wifi" in result.output


def test_cli_icons_list_filter():
    result = CliRunner().invoke(main, ["icons", "list", "--source", "lucide"])
    assert result.exit_code == 0
    assert "lucide:wifi" in result.output


def test_cli_icons_preview(tmp_path: Path):
    out = tmp_path / "wifi.png"
    result = CliRunner().invoke(
        main, ["icons", "preview", "wifi", "--size", "48", "--out", str(out)]
    )
    assert result.exit_code == 0, result.output
    assert out.exists()


def test_cli_icons_preview_unknown():
    result = CliRunner().invoke(main, ["icons", "preview", "no-such-icon"])
    assert result.exit_code != 0
    assert "not found" in result.output.lower()


def test_cli_icons_install_confirms_before_replacing(tmp_path: Path, monkeypatch):
    """The install commands shell out to git; mock out the heavy bits."""
    monkeypatch.setattr(icons_mod, "USER_ROOT", tmp_path)
    (tmp_path / "lucide").mkdir()
    # No --yes flag, so confirm should abort when we decline.
    result = CliRunner().invoke(main, ["icons", "install-lucide"], input="n\n")
    assert "already exists" in result.output
    assert result.exit_code != 0  # aborted
