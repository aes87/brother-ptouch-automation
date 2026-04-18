"""Template registry — discovers built-in packs and entry-point-registered packs."""

from __future__ import annotations

import importlib
import logging
import os
from collections.abc import Iterator
from dataclasses import dataclass, field
from importlib.metadata import entry_points

from label_printer.templates.base import Template
from label_printer.templates.pack import TemplatePack

# Built-in packs shipped with the distribution. Each entry is a ``module:attr``
# import string pointing at a ``TemplatePack`` instance.
BUILTIN_PACK_SPECS: tuple[str, ...] = (
    "label_printer.templates.kitchen:PACK",
    "label_printer.templates.electronics:PACK",
    "label_printer.templates.three_d_printing:PACK",
    "label_printer.templates.utility:PACK",
)

# Entry-point group name for external packs.
ENTRY_POINT_GROUP = "label_printer.packs"

# Operator-facing escape hatch: set to 1/true/yes to skip entry-point discovery.
# Handy for ad-hoc "safe mode" runs when a third-party pack is suspected broken.
DISABLE_ENTRY_POINTS_ENV = "LABEL_PRINTER_DISABLE_ENTRY_POINT_PACKS"

_log = logging.getLogger(__name__)


@dataclass
class Registry:
    templates: dict[str, Template] = field(default_factory=dict)
    packs: dict[str, TemplatePack] = field(default_factory=dict)
    # Packs that failed to load at discovery time. Key: entry-point or spec name.
    failed_packs: dict[str, str] = field(default_factory=dict)

    def register_pack(self, pack: TemplatePack) -> None:
        if pack.name in self.packs:
            raise ValueError(
                f"duplicate pack {pack.name!r}: already registered "
                f"(first v{self.packs[pack.name].version}, now v{pack.version})"
            )
        self.packs[pack.name] = pack
        for template in pack.templates:
            self.templates[template.meta.qualified] = template

    def get(self, qualified_name: str) -> Template:
        if qualified_name not in self.templates:
            available = ", ".join(sorted(self.templates)) or "(none)"
            raise KeyError(
                f"No such template: {qualified_name!r}. Available: {available}"
            )
        return self.templates[qualified_name]

    def by_category(self, category: str) -> list[Template]:
        return [t for t in self.templates.values() if t.meta.category == category]

    def __iter__(self) -> Iterator[Template]:
        return iter(self.templates.values())

    def __len__(self) -> int:
        return len(self.templates)


def _load_pack_spec(spec: str) -> TemplatePack:
    module_name, _, attr = spec.partition(":")
    if not attr:
        raise ValueError(f"bad pack spec {spec!r}: expected 'module:attr'")
    module = importlib.import_module(module_name)
    pack = getattr(module, attr)
    if not isinstance(pack, TemplatePack):
        raise TypeError(f"{spec!r} did not resolve to a TemplatePack (got {type(pack).__name__})")
    return pack


def _env_flag(name: str) -> bool:
    value = os.environ.get(name, "")
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _discover_entry_point_packs() -> Iterator[tuple[str, TemplatePack | Exception]]:
    """Yield (entry-point-name, pack-or-exception) for each registered entry point.

    Failures are yielded as the exception rather than raised so one broken pack
    can't brick the whole CLI. Callers decide whether to record or re-raise.
    """
    for ep in entry_points(group=ENTRY_POINT_GROUP):
        try:
            pack = ep.load()
            if not isinstance(pack, TemplatePack):
                raise TypeError(
                    f"entry-point {ep.name} ({ep.value}) did not resolve to a TemplatePack "
                    f"(got {type(pack).__name__})"
                )
            yield ep.name, pack
        except Exception as exc:  # noqa: BLE001 — intentional isolation
            yield ep.name, exc


def default_registry(include_entry_points: bool = True) -> Registry:
    """Build the registry: built-in packs + (optionally) entry-point packs.

    Entry-point discovery is silently skipped when ``include_entry_points`` is
    False, or when the ``LABEL_PRINTER_DISABLE_ENTRY_POINT_PACKS`` env var is
    set to a truthy value. An external pack that collides with a built-in is
    logged and skipped (built-ins always win); a broken external pack is
    recorded on ``Registry.failed_packs`` so ``lp packs`` can surface it.
    """
    reg = Registry()
    for spec in BUILTIN_PACK_SPECS:
        reg.register_pack(_load_pack_spec(spec))

    if include_entry_points and not _env_flag(DISABLE_ENTRY_POINTS_ENV):
        builtin_names = set(reg.packs)
        for ep_name, result in _discover_entry_point_packs():
            if isinstance(result, Exception):
                reg.failed_packs[ep_name] = f"{type(result).__name__}: {result}"
                _log.warning("entry-point pack %r failed to load: %s", ep_name, result)
                continue
            if result.name in reg.packs:
                other = reg.packs[result.name]
                kind = "built-in" if result.name in builtin_names else "already-loaded external"
                reason = (
                    f"name collision with {kind} pack {result.name!r} "
                    f"(first v{other.version}, this one v{result.version})"
                )
                reg.failed_packs[ep_name] = reason
                _log.warning("entry-point pack %r skipped: %s", ep_name, reason)
                continue
            reg.register_pack(result)
    return reg
