"""Kitchen pack — pantry jars, spice rack, leftovers, freezer."""

from __future__ import annotations

from label_printer.templates.kitchen.freezer import FreezerTemplate
from label_printer.templates.kitchen.leftover import LeftoverTemplate
from label_printer.templates.kitchen.pantry_jar import PantryJarTemplate
from label_printer.templates.kitchen.spice import SpiceTemplate
from label_printer.templates.pack import TemplatePack

PACK = TemplatePack(
    name="kitchen",
    version="0.1.0",
    summary="Kitchen labels — pantry jars, spice rack, leftovers, freezer.",
    templates=(
        PantryJarTemplate(),
        SpiceTemplate(),
        LeftoverTemplate(),
        FreezerTemplate(),
    ),
)
