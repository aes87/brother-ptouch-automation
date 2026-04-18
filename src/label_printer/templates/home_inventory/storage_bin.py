"""Storage bin — location + contents."""

from __future__ import annotations

from PIL import Image

from label_printer.engine.layout import render_two_line_label
from label_printer.tape import TapeWidth
from label_printer.templates.base import Template, TemplateField, TemplateMeta


class StorageBinTemplate(Template):
    meta = TemplateMeta(
        category="home_inventory",
        name="storage_bin",
        summary="Storage bin: shelf/location tag + contents summary.",
        fields=[
            TemplateField("location", "Bin location.", example="Basement bay 3"),
            TemplateField("contents", "Contents summary.", example="Holiday lights"),
            TemplateField("icon", "Optional icon.", required=False, example="box"),
        ],
        default_tape=TapeWidth.MM_12,
    )

    def render(self, data: dict, tape: TapeWidth) -> Image.Image:
        return render_two_line_label(
            tape, str(data["location"]), str(data["contents"]), icon=data.get("icon"),
        )
