"""Utility pack — QR codes, arbitrary images."""

from __future__ import annotations

from label_printer.templates.pack import TemplatePack
from label_printer.templates.utility.image import ImageLabelTemplate
from label_printer.templates.utility.qr import QrTemplate

PACK = TemplatePack(
    name="utility",
    version="0.1.0",
    summary="Utility labels — QR codes, arbitrary images.",
    templates=(
        QrTemplate(),
        ImageLabelTemplate(),
    ),
)
