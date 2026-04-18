"""TemplatePack primitive + registry discovery."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from label_printer.tape import TapeWidth
from label_printer.templates import Registry, TemplatePack, default_registry
from label_printer.templates.base import Template, TemplateField, TemplateMeta
from label_printer.templates.registry import BUILTIN_PACK_SPECS


class _FakeTemplate(Template):
    meta = TemplateMeta(
        category="ham_radio",
        name="callsign",
        summary="Callsign badge.",
        fields=[TemplateField("call", "Operator callsign.", example="W1AW")],
    )

    def render(self, data, tape):
        from PIL import Image
        return Image.new("1", (64, 70), 1)


def test_pack_rejects_mismatched_category():
    with pytest.raises(ValueError, match="category"):
        TemplatePack(
            name="not_ham_radio",
            version="0.1.0",
            summary="bad",
            templates=(_FakeTemplate(),),
        )


def test_pack_iterates_templates():
    pack = TemplatePack(
        name="ham_radio", version="0.1.0", summary="ham", templates=(_FakeTemplate(),)
    )
    assert len(pack) == 1
    assert list(pack)[0].meta.name == "callsign"


def test_registry_refuses_duplicate_pack_name():
    reg = Registry()
    reg.register_pack(TemplatePack(name="kitchen", version="0.1.0", summary="x", templates=()))
    with pytest.raises(ValueError, match="duplicate"):
        reg.register_pack(TemplatePack(name="kitchen", version="0.2.0", summary="y", templates=()))


def test_registry_contains_all_builtin_packs():
    reg = default_registry(include_entry_points=False)
    assert set(reg.packs) == {"kitchen", "electronics", "three_d_printing", "utility"}
    # Every built-in spec should correspond to a loaded pack.
    assert len(reg.packs) == len(BUILTIN_PACK_SPECS)
    for pack in reg.packs.values():
        assert pack.version
        assert pack.templates


def test_registry_default_includes_entry_points_discovery():
    # Simulate an external package registering via entry points.
    fake_pack = TemplatePack(
        name="ham_radio", version="0.1.0", summary="ham radio",
        templates=(_FakeTemplate(),),
    )
    with patch("label_printer.templates.registry._discover_entry_point_packs",
               return_value=iter([("ham_radio_pkg", fake_pack)])):
        reg = default_registry()
    assert "ham_radio" in reg.packs
    assert "ham_radio/callsign" in reg.templates


def test_external_pack_cannot_shadow_builtin():
    shadow = TemplatePack(
        name="kitchen", version="99.0.0", summary="rogue",
        templates=(),
    )
    with patch("label_printer.templates.registry._discover_entry_point_packs",
               return_value=iter([("rogue_kitchen", shadow)])):
        reg = default_registry()
    # Built-in wins.
    assert reg.packs["kitchen"].version == "0.1.0"


def test_two_external_packs_with_same_name_are_reported_not_fatal():
    # First-registered external wins; second is recorded in failed_packs with a
    # warning so operators can diagnose the conflict without the CLI crashing.
    a = TemplatePack(name="ham_radio", version="0.1.0", summary="first", templates=())
    b = TemplatePack(name="ham_radio", version="0.2.0", summary="second", templates=())
    with patch(
        "label_printer.templates.registry._discover_entry_point_packs",
        return_value=iter([("pkg_a", a), ("pkg_b", b)]),
    ):
        reg = default_registry()
    assert reg.packs["ham_radio"].version == "0.1.0"
    assert "pkg_b" in reg.failed_packs
    assert "collision" in reg.failed_packs["pkg_b"]


def test_broken_external_pack_is_isolated_not_fatal():
    class _Boom(Exception):
        pass
    with patch(
        "label_printer.templates.registry._discover_entry_point_packs",
        return_value=iter([("bad_pack", _Boom("broken at import"))]),
    ):
        reg = default_registry()
    assert "bad_pack" in reg.failed_packs
    assert "_Boom" in reg.failed_packs["bad_pack"]
    # Built-ins still loaded — one broken pack doesn't brick the whole CLI.
    assert "kitchen" in reg.packs


def test_env_var_disables_entry_point_discovery(monkeypatch):
    fake_pack = TemplatePack(
        name="ham_radio", version="0.1.0", summary="ham",
        templates=(_FakeTemplate(),),
    )
    monkeypatch.setenv("LABEL_PRINTER_DISABLE_ENTRY_POINT_PACKS", "1")
    with patch(
        "label_printer.templates.registry._discover_entry_point_packs",
        return_value=iter([("ham", fake_pack)]),
    ):
        reg = default_registry()
    assert "ham_radio" not in reg.packs


def test_registered_template_renders_through_registry():
    fake_pack = TemplatePack(
        name="ham_radio", version="0.1.0", summary="ham",
        templates=(_FakeTemplate(),),
    )
    with patch("label_printer.templates.registry._discover_entry_point_packs",
               return_value=iter([("ham_radio_pkg", fake_pack)])):
        reg = default_registry()
    tpl = reg.get("ham_radio/callsign")
    img = tpl.render({"call": "W1AW"}, TapeWidth.MM_12)
    assert img.height == 70
