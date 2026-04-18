"""Patch-panel port — port number + VLAN + optional switch destination."""

from __future__ import annotations

from PIL import Image

from label_printer.engine.layout import render_two_line_label
from label_printer.tape import TapeWidth
from label_printer.templates.base import Template, TemplateField, TemplateMeta


class PatchPortTemplate(Template):
    meta = TemplateMeta(
        category="networking",
        name="patch_port",
        summary="Patch-panel port: port ID + VLAN + optional destination.",
        fields=[
            TemplateField("port", "Port identifier.", example="P12"),
            TemplateField("vlan", "VLAN ID or name.", example="VLAN 20"),
            TemplateField("dest", "Optional destination (switch + port).",
                          required=False, example="sw1 g0/3"),
            TemplateField("icon", "Optional icon.", required=False, example="cable"),
        ],
        default_tape=TapeWidth.MM_12,
    )

    def render(self, data: dict, tape: TapeWidth) -> Image.Image:
        primary = str(data["port"])
        secondary = str(data["vlan"])
        if data.get("dest"):
            secondary = f"{secondary} → {data['dest']}"
        return render_two_line_label(
            tape, primary, secondary, icon=data.get("icon"),
        )
