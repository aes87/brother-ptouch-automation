"""Template pack + registry API."""

from label_printer.templates.base import Template, TemplateField, TemplateMeta
from label_printer.templates.pack import TemplatePack
from label_printer.templates.registry import (
    BUILTIN_PACK_SPECS,
    ENTRY_POINT_GROUP,
    Registry,
    default_registry,
)

__all__ = [
    "Template",
    "TemplateField",
    "TemplateMeta",
    "TemplatePack",
    "Registry",
    "default_registry",
    "BUILTIN_PACK_SPECS",
    "ENTRY_POINT_GROUP",
]
