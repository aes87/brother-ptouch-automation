"""Template auto-discovery.

Walks `src/label_printer/templates/<category>/*.py`, imports each module,
and collects any `Template` subclass with a `meta` attribute.
"""

from __future__ import annotations

import importlib
import pkgutil
from collections.abc import Iterable
from dataclasses import dataclass, field

from label_printer.templates.base import Template

_PACKS = ("kitchen", "electronics", "three_d_printing", "utility")


@dataclass
class Registry:
    templates: dict[str, Template] = field(default_factory=dict)

    def register(self, template: Template) -> None:
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

    def __iter__(self) -> Iterable[Template]:
        return iter(self.templates.values())

    def __len__(self) -> int:
        return len(self.templates)


def _discover_in_pack(pack: str) -> list[Template]:
    pkg_name = f"label_printer.templates.{pack}"
    try:
        pkg = importlib.import_module(pkg_name)
    except ModuleNotFoundError:
        return []
    found: list[Template] = []
    for mod_info in pkgutil.iter_modules(pkg.__path__):
        module = importlib.import_module(f"{pkg_name}.{mod_info.name}")
        for value in vars(module).values():
            if (
                isinstance(value, type)
                and issubclass(value, Template)
                and value is not Template
                and hasattr(value, "meta")
            ):
                found.append(value())
    return found


def default_registry() -> Registry:
    reg = Registry()
    for pack in _PACKS:
        for template in _discover_in_pack(pack):
            reg.register(template)
    return reg
