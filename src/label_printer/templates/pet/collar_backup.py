"""Pet collar backup — pet name + contact phone."""

from __future__ import annotations

from PIL import Image

from label_printer.engine.layout import render_two_line_label
from label_printer.tape import TapeWidth
from label_printer.templates.base import Template, TemplateField, TemplateMeta


class CollarBackupTemplate(Template):
    meta = TemplateMeta(
        category="pet",
        name="collar_backup",
        summary="Pet collar backup: pet name + emergency contact.",
        fields=[
            TemplateField("name", "Pet name.", example="Rex"),
            TemplateField("contact", "Contact phone or info.",
                          example="+1 555 0100"),
            TemplateField("icon", "Optional icon.", required=False, example="paw-print"),
        ],
        default_tape=TapeWidth.MM_12,
    )

    def render(self, data: dict, tape: TapeWidth) -> Image.Image:
        return render_two_line_label(
            tape, str(data["name"]), str(data["contact"]), icon=data.get("icon"),
        )
