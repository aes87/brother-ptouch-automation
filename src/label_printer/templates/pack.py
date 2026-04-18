"""Template pack — the primitive unit of distribution.

A ``TemplatePack`` groups a set of :class:`Template` instances under a
category name. Built-in packs ship with this project; external packs can
install separately and register themselves via the
``label_printer.packs`` entry-point group.

Example (an external package's ``pyproject.toml``)::

    [project.entry-points."label_printer.packs"]
    ham_radio = "label_printer_ham:PACK"

where ``label_printer_ham/__init__.py`` exposes a module-level
``PACK = TemplatePack(...)``.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from label_printer.templates.base import Template


@dataclass(frozen=True)
class TemplatePack:
    """A named, versioned bundle of templates.

    ``name`` becomes the category segment of every contained template's
    qualified name (``<pack>/<template>``). Every template in ``templates``
    must carry a ``meta.category`` matching the pack name — the registry
    rejects mismatches to catch copy-paste bugs early.
    """

    name: str
    version: str
    summary: str
    templates: tuple[Template, ...] = field(default_factory=tuple)
    homepage: str | None = None

    def __post_init__(self) -> None:
        bad = [t for t in self.templates if t.meta.category != self.name]
        if bad:
            names = ", ".join(f"{t.meta.qualified} (category={t.meta.category})" for t in bad)
            raise ValueError(
                f"pack {self.name!r}: templates must have meta.category == {self.name!r}. "
                f"Mismatched: {names}"
            )

    def __iter__(self):
        return iter(self.templates)

    def __len__(self) -> int:
        return len(self.templates)
