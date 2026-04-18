"""Pet pack — collar backups, medication schedules, food bowls."""

from __future__ import annotations

from label_printer.templates.pack import TemplatePack
from label_printer.templates.pet.collar_backup import CollarBackupTemplate
from label_printer.templates.pet.food_bowl import FoodBowlTemplate
from label_printer.templates.pet.med_schedule import MedScheduleTemplate

PACK = TemplatePack(
    name="pet",
    version="0.1.0",
    summary="Pet labels — collar backups, medication schedules, food bowls.",
    templates=(
        CollarBackupTemplate(),
        MedScheduleTemplate(),
        FoodBowlTemplate(),
    ),
)
