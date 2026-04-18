"""Garden pack — seed packets, plant tags, row markers."""

from __future__ import annotations

from label_printer.templates.garden.plant_tag import PlantTagTemplate
from label_printer.templates.garden.row_marker import RowMarkerTemplate
from label_printer.templates.garden.seed_packet import SeedPacketTemplate
from label_printer.templates.pack import TemplatePack

PACK = TemplatePack(
    name="garden",
    version="0.1.0",
    summary="Garden labels — seed packets, plant tags, row markers.",
    templates=(
        SeedPacketTemplate(),
        PlantTagTemplate(),
        RowMarkerTemplate(),
    ),
)
