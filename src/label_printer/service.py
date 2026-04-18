"""HTTP service for remote printing.

Phase 3 ships a dry-run skeleton: `/render` returns a PNG, `/print` returns
the raster command bytes but does NOT send them to a physical printer.
Phase 5 swaps the `/print` endpoint to actually drive USB/BT transport.
"""

from __future__ import annotations

import io
import os
from typing import Any

try:
    from fastapi import FastAPI, Header, HTTPException
    from fastapi.responses import Response
    from pydantic import BaseModel
except ImportError as e:  # pragma: no cover
    raise ImportError(
        "Install service extras: pip install -e '.[service]'"
    ) from e

from label_printer import encode_job
from label_printer.tape import TapeWidth
from label_printer.templates import default_registry

app = FastAPI(title="label-printer", version="0.1.0")
_REGISTRY = default_registry()
_TOKEN_ENV = "LABEL_PRINTER_TOKEN"


def _require_token(authorization: str | None) -> None:
    expected = os.environ.get(_TOKEN_ENV)
    if not expected:
        return  # auth disabled if no token set (local dev)
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "missing bearer token")
    if authorization.split(" ", 1)[1] != expected:
        raise HTTPException(403, "bad token")


class RenderRequest(BaseModel):
    template: str
    tape_mm: int = 12
    fields: dict[str, Any] = {}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "mode": "dry-run"}


@app.get("/templates")
def templates(authorization: str | None = Header(default=None)) -> list[dict[str, Any]]:
    _require_token(authorization)
    return [
        {
            "qualified": t.meta.qualified,
            "summary": t.meta.summary,
            "default_tape_mm": int(t.meta.default_tape),
            "fields": [
                {
                    "name": f.name,
                    "description": f.description,
                    "required": f.required and f.default is None,
                    "default": f.default,
                    "example": f.example,
                }
                for f in t.meta.fields
            ],
        }
        for t in _REGISTRY
    ]


@app.post("/render")
def render(req: RenderRequest, authorization: str | None = Header(default=None)) -> Response:
    _require_token(authorization)
    try:
        template = _REGISTRY.get(req.template)
    except KeyError as e:
        raise HTTPException(404, str(e)) from e
    tape = TapeWidth(4 if req.tape_mm in (3, 4) else req.tape_mm)
    image = template.render(template.validate(req.fields), tape)
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return Response(buf.getvalue(), media_type="image/png")


@app.post("/print")
def print_(req: RenderRequest, authorization: str | None = Header(default=None)) -> Response:
    """Dry-run: returns the raster command bytes. Phase 5 will route to the printer."""
    _require_token(authorization)
    try:
        template = _REGISTRY.get(req.template)
    except KeyError as e:
        raise HTTPException(404, str(e)) from e
    tape = TapeWidth(4 if req.tape_mm in (3, 4) else req.tape_mm)
    image = template.render(template.validate(req.fields), tape)
    data = encode_job(image, tape)
    return Response(
        data,
        media_type="application/octet-stream",
        headers={"X-Dry-Run": "true", "X-Bytes": str(len(data))},
    )
