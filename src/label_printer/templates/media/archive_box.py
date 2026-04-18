"""Archive box — label + retention / destroy-by date."""

from __future__ import annotations

from PIL import Image

from label_printer.engine.layout import render_two_line_label
from label_printer.tape import TapeWidth
from label_printer.templates.base import Template, TemplateField, TemplateMeta


class ArchiveBoxTemplate(Template):
    meta = TemplateMeta(
        category="media",
        name="archive_box",
        summary="Archive box label: identifier + retention / destroy-by date.",
        fields=[
            TemplateField("label", "Box identifier.", example="2024 taxes"),
            TemplateField("retain_until", "Retention expiry.", example="2031-04-15"),
            TemplateField("icon", "Optional icon.", required=False, example="package"),
        ],
        default_tape=TapeWidth.MM_18,
    )

    def render(self, data: dict, tape: TapeWidth) -> Image.Image:
        return render_two_line_label(
            tape, str(data["label"]),
            f"retain until {data['retain_until']}",
            icon=data.get("icon"),
            max_width_mm=180,
        )
