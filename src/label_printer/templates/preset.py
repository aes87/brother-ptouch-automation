"""Preset-driven template: data-defined labels using shared layout helpers.

Most "big line + small line (+ optional icon)" labels differ only in field
names, defaults, and the small-print composition. Expressing those as TOML
presets collapses ~30 near-identical Python files into declarative data and
routes them through a single ``PresetTemplate.render`` that dispatches on
``layout``.

Preset schema (TOML):

    [[presets]]
    qualified = "kitchen/pantry_jar"
    summary   = "Pantry item with purchase date and optional expiry."
    layout    = "two_line"           # currently the only supported layout
    default_tape   = 12              # optional, default 12
    secondary_ratio = 0.28           # optional
    icon_field     = "icon"          # optional — field name carrying a Lucide icon
    handles_extras = []              # optional, e.g. ["link"] to skip compose_extras

    primary = "{name}"
    secondary = [
      "{purchased}",
      { if = "expires", text = " · exp {expires}" },
    ]

    # Optional derived fields computed before string substitution.
    [[presets.derived]]
    name        = "eat_by"
    kind        = "date_offset"
    from_field  = "cooked"
    days_field  = "eat_within_days"

    [[presets.fields]]
    name        = "name"
    description = "Item name."
    required    = true
    example     = "AP Flour"
    # default  = "..."   (optional)

Field templates use ``str.format``-style ``{key}`` placeholders. A
``secondary`` entry that is a table with an ``if`` key renders its ``text``
only when the named field has a truthy value — this is how optional
"appendix" fragments (e.g. "· exp 2027-04-19") are expressed.
"""

from __future__ import annotations

import tomllib
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from PIL import Image

from label_printer.engine.layout import render_two_line_label
from label_printer.tape import TapeWidth
from label_printer.templates.base import Template, TemplateField, TemplateMeta


class PresetTemplate(Template):
    """Template defined entirely by a TOML preset dict."""

    def __init__(self, spec: dict[str, Any]) -> None:
        if "qualified" not in spec:
            raise ValueError("preset missing 'qualified' (e.g. 'kitchen/pantry_jar')")
        category, _, name = spec["qualified"].partition("/")
        if not category or not name:
            raise ValueError(
                f"preset 'qualified' must be 'category/name', got {spec['qualified']!r}"
            )

        fields = []
        for f in spec.get("fields", []):
            fields.append(TemplateField(
                name=f["name"],
                description=f.get("description", ""),
                required=f.get("required", True),
                default=f.get("default"),
                example=f.get("example"),
            ))

        self.spec = spec
        self.meta = TemplateMeta(
            category=category,
            name=name,
            summary=spec.get("summary", ""),
            fields=fields,
            default_tape=TapeWidth(int(spec.get("default_tape", 12))),
        )
        self.handles_extras = frozenset(spec.get("handles_extras", []))

    def render(self, data: dict[str, Any], tape: TapeWidth) -> Image.Image:
        # Apply any derived fields before string substitution so {eat_by}-style
        # references resolve.
        enriched = dict(data)
        for derived in self.spec.get("derived", ()):
            enriched[derived["name"]] = self._compute_derived(derived, enriched)

        layout = self.spec.get("layout", "two_line")
        if layout == "two_line":
            return self._render_two_line(enriched, tape)
        raise ValueError(f"preset {self.meta.qualified} uses unknown layout {layout!r}")

    # ---- layout: two_line -----------------------------------------------

    def _render_two_line(self, data: dict[str, Any], tape: TapeWidth) -> Image.Image:
        primary = self._render_line(
            simple=self.spec.get("primary"),
            parts=self.spec.get("primary_parts"),
            join=self.spec.get("primary_join"),
            data=data,
        )
        secondary = self._render_line(
            simple=None,
            parts=self.spec.get("secondary"),
            join=self.spec.get("secondary_join"),
            data=data,
        )
        icon = None
        if (icon_field := self.spec.get("icon_field")):
            icon_value = data.get(icon_field)
            if icon_value:
                icon = str(icon_value)
        return render_two_line_label(
            tape,
            primary,
            secondary,
            icon=icon,
            secondary_ratio=float(self.spec.get("secondary_ratio", 0.28)),
            max_width_mm=float(self.spec.get("max_width_mm", 120.0)),
            padding_mm=float(self.spec.get("padding_mm", 6.0)),
        )

    def _render_line(self, *, simple: str | None, parts: Any,
                     join: str | None, data: dict[str, Any]) -> str:
        """Build a single text line — either from a plain string template or a
        parts list of plain strings / conditional tables. ``join`` inserts a
        separator between non-empty parts (skipped when None, in which case
        parts concatenate)."""
        if simple is not None and not parts:
            return self._fmt(simple, data)

        rendered: list[str] = []
        for entry in (parts or ()):
            if isinstance(entry, str):
                rendered.append(self._fmt(entry, data))
            elif isinstance(entry, dict):
                if not self._entry_matches(entry, data):
                    continue
                rendered.append(self._fmt(entry.get("text", ""), data))
            else:
                raise ValueError(
                    f"preset {self.meta.qualified}: unrecognised line entry {entry!r}"
                )

        if join is None:
            return "".join(rendered)
        return str(join).join(p for p in rendered if p)

    @staticmethod
    def _is_truthy(value: Any) -> bool:
        """Treat common string sentinels like 'no' / 'false' / '0' as falsy."""
        if value is None:
            return False
        if isinstance(value, str):
            return value.strip().lower() not in ("", "no", "false", "0", "none")
        return bool(value)

    @classmethod
    def _entry_matches(cls, entry: dict[str, Any], data: dict[str, Any]) -> bool:
        if "if" in entry:
            return cls._is_truthy(data.get(entry["if"]))
        if "if_all" in entry:
            return all(cls._is_truthy(data.get(k)) for k in entry["if_all"])
        if "if_any" in entry:
            return any(cls._is_truthy(data.get(k)) for k in entry["if_any"])
        return True  # unconditional table entry

    # ---- substitution + derived ----------------------------------------

    def _fmt(self, template: str, data: dict[str, Any]) -> str:
        # None-valued fields become empty strings so optional slots don't print
        # "None". Missing keys raise KeyError (caller's schema is wrong).
        safe = {k: ("" if v is None else v) for k, v in data.items()}
        try:
            return template.format(**safe)
        except KeyError as e:
            raise ValueError(
                f"preset {self.meta.qualified}: template {template!r} references "
                f"unknown field {e}"
            ) from e

    def _compute_derived(self, spec: dict[str, Any], data: dict[str, Any]) -> Any:
        kind = spec.get("kind")
        if kind == "date_offset":
            base_val = data.get(spec["from_field"])
            if not base_val:
                return ""
            base = date.fromisoformat(str(base_val))
            days_raw = data.get(spec["days_field"], 0)
            days = int(days_raw if days_raw not in (None, "") else 0)
            return (base + timedelta(days=days)).isoformat()
        raise ValueError(
            f"preset {self.meta.qualified}: unknown derived kind {kind!r}"
        )


def load_presets(toml_path: str | Path) -> list[PresetTemplate]:
    """Load all presets declared in a TOML file as ``PresetTemplate`` instances.

    Returns an empty list if the file doesn't exist — lets packs ship without
    a preset file if they're all bespoke.
    """
    path = Path(toml_path)
    if not path.exists():
        return []
    with path.open("rb") as f:
        doc = tomllib.load(f)
    return [PresetTemplate(entry) for entry in doc.get("presets", ())]
