"""Calibration certificate ID — cert number + issuer."""

from __future__ import annotations

from PIL import Image

from label_printer.engine.layout import render_two_line_label
from label_printer.tape import TapeWidth
from label_printer.templates.base import Template, TemplateField, TemplateMeta


class CertIdTemplate(Template):
    meta = TemplateMeta(
        category="calibration",
        name="cert_id",
        summary="Calibration certificate reference: cert number + issuer.",
        fields=[
            TemplateField("cert_no", "Certificate number.", example="CAL-2026-00421"),
            TemplateField("issuer", "Issuing lab / standard.",
                          example="ISO/IEC 17025"),
            TemplateField("icon", "Optional icon.", required=False,
                          example="file-text"),
        ],
        default_tape=TapeWidth.MM_12,
    )

    def render(self, data: dict, tape: TapeWidth) -> Image.Image:
        return render_two_line_label(
            tape, str(data["cert_no"]), str(data["issuer"]),
            icon=data.get("icon"),
        )
