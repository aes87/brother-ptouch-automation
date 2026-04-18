"""3D-printing pack — filament spools, print bins, tool tags."""

from __future__ import annotations

from label_printer.templates.pack import TemplatePack
from label_printer.templates.three_d_printing.filament_spool import FilamentSpoolTemplate
from label_printer.templates.three_d_printing.print_bin import PrintBinTemplate
from label_printer.templates.three_d_printing.tool_tag import ToolTagTemplate

PACK = TemplatePack(
    name="three_d_printing",
    version="0.1.0",
    summary="3D-printing labels — filament spools, print bins, tool tags.",
    templates=(
        FilamentSpoolTemplate(),
        PrintBinTemplate(),
        ToolTagTemplate(),
    ),
)
