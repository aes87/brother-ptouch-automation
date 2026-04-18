"""Template registry for label definitions."""

from label_printer.templates.base import Template, TemplateField
from label_printer.templates.registry import Registry, default_registry

__all__ = ["Template", "TemplateField", "Registry", "default_registry"]
