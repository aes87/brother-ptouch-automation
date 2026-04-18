"""Calibration pack — instrument cal stickers, certificate IDs, thermometer checks."""

from __future__ import annotations

from label_printer.templates.calibration.cert_id import CertIdTemplate
from label_printer.templates.calibration.instrument_cal import InstrumentCalTemplate
from label_printer.templates.calibration.thermometer_cal import ThermometerCalTemplate
from label_printer.templates.pack import TemplatePack

PACK = TemplatePack(
    name="calibration",
    version="0.1.0",
    summary="Calibration labels — instrument cal, cert IDs, thermometer checks.",
    templates=(
        InstrumentCalTemplate(),
        CertIdTemplate(),
        ThermometerCalTemplate(),
    ),
)
