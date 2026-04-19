"""Electronics pack — cable flags, parts bins, PSU polarity."""

from __future__ import annotations

from label_printer.templates.electronics.cable_flag import CableFlagTemplate
from label_printer.templates.electronics.cable_flag_qr import CableFlagQrTemplate
from label_printer.templates.electronics.component_bin import ComponentBinTemplate
from label_printer.templates.electronics.psu_polarity import PsuPolarityTemplate
from label_printer.templates.pack import TemplatePack

PACK = TemplatePack(
    name="electronics",
    version="0.2.0",
    summary="Electronics labels — cable flags, parts bins, PSU polarity.",
    templates=(
        CableFlagTemplate(),
        CableFlagQrTemplate(),
        ComponentBinTemplate(),
        PsuPolarityTemplate(),
    ),
)
