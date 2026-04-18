"""CD / record — title + artist."""

from __future__ import annotations

from PIL import Image

from label_printer.engine.layout import render_two_line_label
from label_printer.tape import TapeWidth
from label_printer.templates.base import Template, TemplateField, TemplateMeta


class CdRecordTemplate(Template):
    meta = TemplateMeta(
        category="media",
        name="cd_record",
        summary="Music media: title + artist + optional year.",
        fields=[
            TemplateField("title", "Album title.", example="Kind of Blue"),
            TemplateField("artist", "Artist.", example="Miles Davis"),
            TemplateField("year", "Optional release year.", required=False, example="1959"),
            TemplateField("icon", "Optional icon.", required=False, example="bookmark"),
        ],
        default_tape=TapeWidth.MM_12,
    )

    def render(self, data: dict, tape: TapeWidth) -> Image.Image:
        sub = str(data["artist"])
        if data.get("year"):
            sub = f"{sub} · {data['year']}"
        return render_two_line_label(
            tape, str(data["title"]), sub, icon=data.get("icon"),
        )
