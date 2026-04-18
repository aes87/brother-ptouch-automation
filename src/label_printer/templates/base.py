"""Template base class and field schema.

A Template declares a small schema of named fields (so the CLI and the skill
can introspect what data it needs), and a `render(data, tape) -> Image`
method that produces a label image.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from PIL import Image

from label_printer.tape import TapeWidth


@dataclass(frozen=True)
class TemplateField:
    name: str
    description: str
    required: bool = True
    default: Any = None
    example: str | None = None


@dataclass(frozen=True)
class TemplateMeta:
    category: str
    name: str
    summary: str
    fields: list[TemplateField] = field(default_factory=list)
    default_tape: TapeWidth = TapeWidth.MM_12

    @property
    def qualified(self) -> str:
        return f"{self.category}/{self.name}"


class Template(ABC):
    meta: TemplateMeta

    @abstractmethod
    def render(self, data: dict[str, Any], tape: TapeWidth) -> Image.Image:
        """Render the label. Return a Pillow image sized for the given tape."""

    # Convenience, but subclasses can override.
    def validate(self, data: dict[str, Any]) -> dict[str, Any]:
        resolved: dict[str, Any] = {}
        for field_spec in self.meta.fields:
            if field_spec.name in data:
                resolved[field_spec.name] = data[field_spec.name]
            elif field_spec.required and field_spec.default is None:
                raise ValueError(
                    f"Template {self.meta.qualified} is missing required field "
                    f"'{field_spec.name}'"
                )
            else:
                resolved[field_spec.name] = field_spec.default
        return resolved
