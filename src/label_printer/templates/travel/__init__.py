"""Travel pack — luggage tags, gear bags, power banks."""

from __future__ import annotations

from label_printer.templates.pack import TemplatePack
from label_printer.templates.travel.gear_bag import GearBagTemplate
from label_printer.templates.travel.luggage_tag import LuggageTagTemplate
from label_printer.templates.travel.power_bank import PowerBankTemplate

PACK = TemplatePack(
    name="travel",
    version="0.1.0",
    summary="Travel labels — luggage tags, gear bags, power banks.",
    templates=(
        LuggageTagTemplate(),
        GearBagTemplate(),
        PowerBankTemplate(),
    ),
)
