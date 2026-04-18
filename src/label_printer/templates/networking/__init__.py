"""Networking pack — patch ports, rack units, WAP locations."""

from __future__ import annotations

from label_printer.templates.networking.patch_port import PatchPortTemplate
from label_printer.templates.networking.rack_unit import RackUnitTemplate
from label_printer.templates.networking.wap_location import WapLocationTemplate
from label_printer.templates.pack import TemplatePack

PACK = TemplatePack(
    name="networking",
    version="0.1.0",
    summary="Network labels — patch ports, rack units, access points.",
    templates=(
        PatchPortTemplate(),
        RackUnitTemplate(),
        WapLocationTemplate(),
    ),
)
