"""Bookshelf tag — title + author + optional call number."""

from __future__ import annotations

from PIL import Image

from label_printer.engine.layout import render_two_line_label
from label_printer.tape import TapeWidth
from label_printer.templates.base import Template, TemplateField, TemplateMeta


class BookshelfTagTemplate(Template):
    meta = TemplateMeta(
        category="media",
        name="bookshelf_tag",
        summary="Bookshelf tag: title + author + optional call number.",
        fields=[
            TemplateField("title", "Book title.", example="Refactoring"),
            TemplateField("author", "Author.", example="Fowler"),
            TemplateField("callno", "Optional call number / shelf code.",
                          required=False, example="QA76.F69"),
            TemplateField("icon", "Optional icon.", required=False, example="book"),
        ],
        default_tape=TapeWidth.MM_12,
    )

    def render(self, data: dict, tape: TapeWidth) -> Image.Image:
        sub = str(data["author"])
        if data.get("callno"):
            sub = f"{sub} · {data['callno']}"
        return render_two_line_label(
            tape, str(data["title"]), sub, icon=data.get("icon"),
        )
