"""Luggage tag — name + contact."""

from __future__ import annotations

from PIL import Image

from label_printer.engine.layout import render_two_line_label
from label_printer.tape import TapeWidth
from label_printer.templates.base import Template, TemplateField, TemplateMeta


class LuggageTagTemplate(Template):
    meta = TemplateMeta(
        category="travel",
        name="luggage_tag",
        summary="Luggage / gear tag: name + contact (phone or email).",
        fields=[
            TemplateField("name", "Owner name.", example="aes87"),
            TemplateField("contact", "Phone or email.", example="aesthe@example.com"),
            TemplateField("icon", "Optional icon.", required=False, example="luggage"),
        ],
        default_tape=TapeWidth.MM_18,
    )

    def render(self, data: dict, tape: TapeWidth) -> Image.Image:
        return render_two_line_label(
            tape, str(data["name"]), str(data["contact"]),
            icon=data.get("icon"), max_width_mm=180,
        )
