"""Kitchen pack — pantry jars, spice rack, leftovers, freezer.

All four templates are preset-driven; see ``presets.toml``. The pack's
version bumps whenever a preset field changes in a backwards-incompatible
way so downstream callers can pin.
"""

from __future__ import annotations

from pathlib import Path

from label_printer.templates.pack import TemplatePack
from label_printer.templates.preset import load_presets

PACK = TemplatePack(
    name="kitchen",
    version="0.2.0",
    summary="Kitchen labels — pantry jars, spice rack, leftovers, freezer.",
    templates=tuple(load_presets(Path(__file__).parent / "presets.toml")),
)
