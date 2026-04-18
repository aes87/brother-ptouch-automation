"""HTTP service smoke tests."""

from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from label_printer.service import app  # noqa: E402


@pytest.fixture
def client():
    return TestClient(app)


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["mode"] == "dry-run"


def test_templates(client):
    r = client.get("/templates")
    assert r.status_code == 200
    names = {t["qualified"] for t in r.json()}
    assert "kitchen/pantry_jar" in names
    assert "three_d_printing/filament_spool" in names


def test_render_returns_png(client):
    r = client.post("/render", json={
        "template": "kitchen/pantry_jar",
        "tape_mm": 12,
        "fields": {"name": "FLOUR", "purchased": "2026-04-19"},
    })
    assert r.status_code == 200
    assert r.headers["content-type"] == "image/png"
    assert r.content[:8] == b"\x89PNG\r\n\x1a\n"


def test_print_dryrun_returns_raster(client):
    r = client.post("/print", json={
        "template": "kitchen/spice",
        "tape_mm": 12,
        "fields": {"name": "Paprika"},
    })
    assert r.status_code == 200
    assert r.headers["x-dry-run"] == "true"
    assert int(r.headers["x-bytes"]) == len(r.content)
    assert r.content.endswith(b"\x1a")


def test_auth_when_token_set(client, monkeypatch):
    monkeypatch.setenv("LABEL_PRINTER_TOKEN", "s3cret")
    r = client.get("/templates")
    assert r.status_code == 401
    r = client.get("/templates", headers={"Authorization": "Bearer wrong"})
    assert r.status_code == 403
    r = client.get("/templates", headers={"Authorization": "Bearer s3cret"})
    assert r.status_code == 200


def test_missing_template_404(client):
    r = client.post("/render", json={"template": "nope/nope", "tape_mm": 12, "fields": {}})
    assert r.status_code == 404
