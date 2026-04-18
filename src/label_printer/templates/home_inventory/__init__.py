"""Home-inventory pack — moving boxes, warranties, storage bins."""

from __future__ import annotations

from label_printer.templates.home_inventory.moving_box import MovingBoxTemplate
from label_printer.templates.home_inventory.storage_bin import StorageBinTemplate
from label_printer.templates.home_inventory.warranty import WarrantyTemplate
from label_printer.templates.pack import TemplatePack

PACK = TemplatePack(
    name="home_inventory",
    version="0.1.0",
    summary="Home-inventory labels — moving boxes, warranties, storage bins.",
    templates=(
        MovingBoxTemplate(),
        WarrantyTemplate(),
        StorageBinTemplate(),
    ),
)
