"""Tape width definitions and print-area geometry.

The PT-P710BT print head is 128 pins wide. Tape narrower than 24 mm leaves
equal margins on both sides of the head, so a narrower tape uses fewer pins
for the actual print. The per-tape margin values below are taken from the
Brother Raster Command Reference.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum

from label_printer.constants import PRINT_HEAD_PINS


class TapeWidth(IntEnum):
    """Supported TZe tape widths in millimetres.

    The `status` packet reports width in mm as well, so IntEnum values mirror
    the protocol-level integer directly.
    """

    MM_3_5 = 4   # reported as 4 by the printer
    MM_6 = 6
    MM_9 = 9
    MM_12 = 12
    MM_18 = 18
    MM_24 = 24


# Margin (in pins) left empty on EACH side of the 128-pin head for a given tape width.
# Source: Brother Raster Command Reference, "Print Head/Tape Relationship".
_MARGIN_PINS: dict[TapeWidth, int] = {
    TapeWidth.MM_3_5: 52,
    TapeWidth.MM_6: 48,
    TapeWidth.MM_9: 39,
    TapeWidth.MM_12: 29,
    TapeWidth.MM_18: 8,
    TapeWidth.MM_24: 0,
}


@dataclass(frozen=True)
class TapeGeometry:
    width: TapeWidth
    margin_pins: int
    print_pins: int

    @property
    def display_mm(self) -> float:
        return 3.5 if self.width == TapeWidth.MM_3_5 else float(int(self.width))


def geometry_for(tape: TapeWidth) -> TapeGeometry:
    margin = _MARGIN_PINS[tape]
    return TapeGeometry(
        width=tape,
        margin_pins=margin,
        print_pins=PRINT_HEAD_PINS - 2 * margin,
    )
