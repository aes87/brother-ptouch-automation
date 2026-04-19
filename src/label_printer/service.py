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
from label_printer.engine.compose import compose_extras, strip_template_handled
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
    # Optional post-render extras composed onto the right edge of any label.
    link: str | None = None
    image: str | None = None


def _render_body_with_extras(template, fields: dict, tape: TapeWidth,
                             link: str | None, image: str | None):
    extras = {k: v for k, v in {"link": link, "image": image}.items() if v}
    extras = strip_template_handled(extras, template)
    body = template.render(template.validate(fields), tape)
    return compose_extras(body, extras, tape)


class PrintRequest(RenderRequest):
    # Dry-run by default — opt in explicitly to drive the hardware transport.
    # Until Phase 5 lands, ``send=True`` will 501 because no transport is wired.
    send: bool = False


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
    image = _render_body_with_extras(template, req.fields, tape, req.link, req.image)
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return Response(buf.getvalue(), media_type="image/png")


@app.post("/print")
def print_(req: PrintRequest, authorization: str | None = Header(default=None)) -> Response:
    """Encode a label. Dry-run by default; set ``send=true`` to drive the printer."""
    _require_token(authorization)
    try:
        template = _REGISTRY.get(req.template)
    except KeyError as e:
        raise HTTPException(404, str(e)) from e
    tape = TapeWidth(4 if req.tape_mm in (3, 4) else req.tape_mm)
    image = _render_body_with_extras(template, req.fields, tape, req.link, req.image)
    data = encode_job(image, tape)

    if req.send:
        raise HTTPException(
            501,
            "hardware transport not available yet (arrives in Phase 5). "
            "Omit 'send' or set it to false for a dry-run.",
        )

    return Response(
        data,
        media_type="application/octet-stream",
        headers={"X-Dry-Run": "true", "X-Bytes": str(len(data))},
    )
