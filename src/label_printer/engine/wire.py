"""Wire / cable size lookup for wrap-around cable flag sizing.

Callers typically pass a plain-language string — ``"ethernet"``, ``"usb-c"``,
``"18 AWG"``, ``"5mm"`` — and we resolve it to an outer diameter in
millimetres. That diameter drives the length of the wrap section on a
cable flag (π·OD + adhesive overlap).

All values are approximate outer diameters including jacket / insulation.
They're tuned for "typical" installations — thin Cat6 patch, consumer USB,
standard-duty appliance power — and can be overridden with a literal mm
value (``"7mm"``) when in doubt.
"""

from __future__ import annotations

import math
import re

# Outer diameter in mm for common cable types. Keys are normalised
# (lowercase, no whitespace, no punctuation except '-').
_CABLE_OD_MM: dict[str, float] = {
    # -- Networking ---------------------------------------------------------
    "ethernet": 5.5,
    "cat5": 5.0,
    "cat5e": 5.2,
    "cat6": 5.5,
    "cat6a": 7.5,
    "cat7": 7.5,
    "cat8": 8.0,
    "fiber": 3.0,
    "fiber-duplex": 4.5,
    "sc-fiber": 3.0,
    "lc-fiber": 2.8,
    "coax": 7.0,
    "rg6": 7.0,
    "rg58": 5.0,
    "rg59": 6.1,
    # -- Audio/video --------------------------------------------------------
    "hdmi": 7.0,
    "hdmi-thin": 5.5,
    "displayport": 7.0,
    "dp": 7.0,
    "vga": 8.5,
    "dvi": 9.0,
    "rca": 5.0,
    "3.5mm": 3.5,
    "headphone": 3.5,
    "toslink": 5.0,
    "speakon": 10.0,
    "xlr": 7.0,
    "trs": 6.3,
    "sdi": 7.0,
    # -- Computing / data ---------------------------------------------------
    "usb": 3.5,
    "usb-a": 3.5,
    "usb-b": 4.5,
    "usb-c": 3.5,
    "usb-c-pd": 4.5,
    "micro-usb": 3.0,
    "mini-usb": 3.5,
    "lightning": 3.0,
    "thunderbolt": 4.5,
    "thunderbolt-4": 4.5,
    "firewire": 6.0,
    "sata": 5.0,
    "esata": 5.5,
    "dvi-d": 9.0,
    # -- Power --------------------------------------------------------------
    "ac": 8.0,
    "power": 8.0,
    "iec": 7.5,
    "iec-c13": 7.5,
    "iec-c19": 9.0,
    "lamp-cord": 6.0,
    "spt-1": 5.5,
    "spt-2": 6.5,
    "extension-cord": 10.0,
    "extension": 10.0,
    "heavy-extension": 12.0,
    "nema-5-15": 8.0,
    "kettle": 7.5,
    "dc-barrel": 3.5,
    "molex": 7.0,
    "dc-wire": 4.0,
    "mains": 9.0,
    # -- Hobby / electronics ------------------------------------------------
    "jst": 2.5,
    "dupont": 1.5,
    "ribbon": 1.3,  # per-conductor thickness
    "breadboard-jumper": 1.5,
    "silicone-hookup": 2.2,
    "speaker-wire": 5.0,
    "solid-core": 1.7,
    "thhn": 3.5,
    "romex-14": 9.0,
    "romex-12": 10.0,
    "romex-10": 11.5,
    # -- IoT / comms --------------------------------------------------------
    "zigbee-antenna": 3.0,
    "gpio": 1.5,
    "can": 6.0,
    "modbus": 6.0,
    "dmx": 6.5,
}

# AWG → approximate insulated-wire OD in mm.
# Stranded hookup wire with standard PVC insulation, single conductor.
_AWG_OD_MM: dict[int, float] = {
    30: 0.8,
    28: 1.0,
    26: 1.1,
    24: 1.4,
    22: 1.7,
    20: 2.0,
    18: 2.6,
    16: 3.2,
    14: 3.8,
    12: 4.5,
    10: 5.5,
    8: 6.5,
    6: 8.0,
    4: 9.5,
    2: 11.5,
    0: 13.0,
}

_AWG_RE = re.compile(r"^\s*(\d{1,2})\s*(awg|ga|gauge)?\s*$", re.IGNORECASE)
_MM_RE = re.compile(r"^\s*([0-9]*\.?[0-9]+)\s*mm\s*$", re.IGNORECASE)


class UnknownWireError(ValueError):
    pass


def _normalise(spec: str) -> str:
    return re.sub(r"\s+", "", spec).lower().replace("_", "-")


def diameter_mm(spec: str | float | int) -> float:
    """Resolve a wire / cable descriptor to an outer diameter in mm.

    Accepts:
      - a float/int → interpreted as mm directly
      - ``"<n>mm"`` → literal mm
      - ``"<n>AWG"`` / ``"<n> ga"`` / ``"<n>"`` between 0 and 30 → AWG table
      - a keyword from the cable table (``"ethernet"``, ``"usb-c"``, ...)
    """
    if isinstance(spec, (int, float)) and not isinstance(spec, bool):
        return float(spec)

    text = str(spec).strip()
    if not text:
        raise UnknownWireError("empty wire spec")

    if (m := _MM_RE.match(text)):
        return float(m.group(1))

    key = _normalise(text)

    if (m := _AWG_RE.match(text)):
        n = int(m.group(1))
        if n in _AWG_OD_MM:
            return _AWG_OD_MM[n]
        if m.group(2):
            raise UnknownWireError(f"unsupported AWG: {n}")
        # Bare number — only treat as AWG when it's plausibly an AWG value.
        # Otherwise fall through to the keyword lookup for keys like '3.5mm'.

    if key in _CABLE_OD_MM:
        return _CABLE_OD_MM[key]

    # Plain integer without AWG suffix and not a keyword → AWG fallback.
    if text.isdigit() and (n := int(text)) in _AWG_OD_MM:
        return _AWG_OD_MM[n]

    raise UnknownWireError(
        f"unknown wire spec: {spec!r}. Pass a keyword (e.g. 'ethernet'), an AWG ('18 AWG'), "
        f"or a literal diameter ('5mm')."
    )


def wrap_length_mm(od_mm: float, overlap_mm: float = 3.0) -> float:
    """Minimum wrap-section length for a cable of given outer diameter.

    Returns π × OD (one full turn around the cable) plus an overlap margin
    so the adhesive has somewhere to land on itself.
    """
    return math.pi * od_mm + overlap_mm


def known_specs() -> list[str]:
    """List all supported keyword descriptors (sorted). Useful for CLI help."""
    return sorted(_CABLE_OD_MM)


def known_awg() -> list[int]:
    return sorted(_AWG_OD_MM, reverse=True)
