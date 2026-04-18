"""Moving box — room + contents + optional fragility flag."""

from __future__ import annotations

from PIL import Image

from label_printer.engine.layout import render_two_line_label
from label_printer.tape import TapeWidth
from label_printer.templates.base import Template, TemplateField, TemplateMeta


class MovingBoxTemplate(Template):
    meta = TemplateMeta(
        category="home_inventory",
        name="moving_box",
        summary="Moving / storage box: destination room + contents summary.",
        fields=[
            TemplateField("room", "Destination room.", example="Kitchen"),
            TemplateField("contents", "Contents summary.", example="pots, cutting boards"),
            TemplateField("fragile", "Optional fragility flag ('yes' to add a mark).",
                          required=False, default="no"),
            TemplateField("icon", "Optional icon.", required=False, example="package"),
        ],
        default_tape=TapeWidth.MM_24,
    )

    def render(self, data: dict, tape: TapeWidth) -> Image.Image:
        primary = str(data["room"])
        if str(data.get("fragile") or "").lower() in ("yes", "true", "1"):
            primary = f"{primary} · FRAGILE"
        return render_two_line_label(
            tape, primary, str(data["contents"]),
            icon=data.get("icon"), max_width_mm=200,
        )
