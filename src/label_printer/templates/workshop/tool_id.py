"""Tool ID — name + owner + optional project."""

from __future__ import annotations

from PIL import Image

from label_printer.engine.layout import render_two_line_label
from label_printer.tape import TapeWidth
from label_printer.templates.base import Template, TemplateField, TemplateMeta


class ToolIdTemplate(Template):
    meta = TemplateMeta(
        category="workshop",
        name="tool_id",
        summary="Workshop tool ID: name + owner + optional project.",
        fields=[
            TemplateField("name", "Tool name.", example="Cordless drill"),
            TemplateField("owner", "Owner or location.", example="aes / garage"),
            TemplateField("project", "Optional project or set.", required=False,
                          example="Makita set"),
            TemplateField("icon", "Optional icon.", required=False, example="wrench"),
        ],
        default_tape=TapeWidth.MM_12,
    )

    def render(self, data: dict, tape: TapeWidth) -> Image.Image:
        sub = str(data["owner"])
        if data.get("project"):
            sub = f"{sub} · {data['project']}"
        return render_two_line_label(
            tape, str(data["name"]), sub, icon=data.get("icon"),
        )
