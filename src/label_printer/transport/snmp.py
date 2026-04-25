"""Minimal SNMP v2c client for printer status queries.

Brother PT-series network firmware treats TCP:9100 as a write-only print
endpoint — ``ESC i S`` is silently dropped. The standard escape hatch is
SNMP on UDP:161, which exposes the Printer MIB (RFC 3805). We only need
GET on a handful of OIDs (tape width, errors), so this module hand-rolls
a minimal ASN.1 BER encoder rather than pulling in ``pysnmp``.

The ASN.1 surface we need:

* INTEGER, OCTET STRING, NULL, OBJECT IDENTIFIER (primitives)
* SEQUENCE (constructed)
* SNMP-PDU GetRequest (constructed, tag 0xA0)

Output format from :func:`snmp_get` is the decoded Python-native value of
the requested OID (int / str / bytes / None) — callers don't need to think
about ASN.1.
"""

from __future__ import annotations

import os
import socket

# --- ASN.1 BER tags ---------------------------------------------------------

_TAG_INTEGER = 0x02
_TAG_OCTET_STRING = 0x04
_TAG_NULL = 0x05
_TAG_OID = 0x06
_TAG_SEQUENCE = 0x30
_TAG_GET_REQUEST = 0xA0
_TAG_GET_RESPONSE = 0xA2

_DEFAULT_TIMEOUT = 1.0  # 1 s per OID is plenty on a LAN; printer is one hop away.
_DEFAULT_COMMUNITY = "public"
_SNMP_PORT = 161


# --- Encoder ----------------------------------------------------------------


def _encode_length(n: int) -> bytes:
    if n < 0x80:
        return bytes([n])
    body = n.to_bytes((n.bit_length() + 7) // 8, "big")
    return bytes([0x80 | len(body)]) + body


def _tlv(tag: int, value: bytes) -> bytes:
    return bytes([tag]) + _encode_length(len(value)) + value


def _enc_int(n: int) -> bytes:
    if n == 0:
        body = b"\x00"
    else:
        # Two's-complement, smallest representation (with leading 0x00 for
        # positive values whose top bit would otherwise look negative).
        nbytes = (n.bit_length() // 8) + 1
        body = n.to_bytes(nbytes, "big", signed=True)
    return _tlv(_TAG_INTEGER, body)


def _enc_octet_string(s: bytes) -> bytes:
    return _tlv(_TAG_OCTET_STRING, s)


def _enc_null() -> bytes:
    return _tlv(_TAG_NULL, b"")


def _enc_oid(oid: str) -> bytes:
    parts = [int(p) for p in oid.split(".")]
    if len(parts) < 2:
        raise ValueError(f"OID needs at least two arcs: {oid!r}")
    body = bytearray([parts[0] * 40 + parts[1]])
    for n in parts[2:]:
        if n < 0:
            raise ValueError(f"negative arc in OID: {oid!r}")
        if n == 0:
            body.append(0)
            continue
        # Base-128, MSB-first; high bit set on every byte except the last.
        chunks = []
        while n > 0:
            chunks.append(n & 0x7F)
            n >>= 7
        for i in range(len(chunks) - 1, 0, -1):
            body.append(chunks[i] | 0x80)
        body.append(chunks[0])
    return _tlv(_TAG_OID, bytes(body))


def _enc_sequence(*items: bytes) -> bytes:
    return _tlv(_TAG_SEQUENCE, b"".join(items))


def _build_get_request(oid: str, request_id: int, community: str) -> bytes:
    varbind = _enc_sequence(_enc_oid(oid), _enc_null())
    varbinds = _enc_sequence(varbind)
    pdu = _tlv(
        _TAG_GET_REQUEST,
        _enc_int(request_id)
        + _enc_int(0)  # error-status
        + _enc_int(0)  # error-index
        + varbinds,
    )
    return _enc_sequence(
        _enc_int(1),  # version: 1 == SNMPv2c
        _enc_octet_string(community.encode()),
        pdu,
    )


# --- Decoder ----------------------------------------------------------------


class SnmpError(RuntimeError):
    """Raised for malformed SNMP responses or non-zero error-status."""


def _decode_length(data: bytes, pos: int) -> tuple[int, int]:
    if pos >= len(data):
        raise SnmpError("truncated TLV: length byte past end-of-buffer")
    first = data[pos]
    pos += 1
    if first < 0x80:
        return first, pos
    nbytes = first & 0x7F
    if nbytes == 0:
        raise SnmpError("indefinite-length encoding not supported")
    if pos + nbytes > len(data):
        raise SnmpError("truncated TLV: length-prefix runs past end-of-buffer")
    length = int.from_bytes(data[pos : pos + nbytes], "big")
    return length, pos + nbytes


def _decode_tlv(data: bytes, pos: int) -> tuple[int, bytes, int]:
    if pos >= len(data):
        raise SnmpError("truncated TLV: tag byte past end-of-buffer")
    tag = data[pos]
    pos += 1
    length, pos = _decode_length(data, pos)
    if pos + length > len(data):
        raise SnmpError(
            f"truncated TLV: declared length {length} runs past end-of-buffer"
        )
    return tag, data[pos : pos + length], pos + length


def _decode_int(data: bytes) -> int:
    if not data:
        return 0
    return int.from_bytes(data, "big", signed=True)


def _decode_oid(data: bytes) -> str:
    if not data:
        return ""
    arcs = [data[0] // 40, data[0] % 40]
    accum = 0
    for byte in data[1:]:
        accum = (accum << 7) | (byte & 0x7F)
        if not (byte & 0x80):
            arcs.append(accum)
            accum = 0
    return ".".join(str(a) for a in arcs)


def _decode_value(tag: int, data: bytes):
    if tag == _TAG_INTEGER or tag in (0x41, 0x42, 0x43, 0x44, 0x46):
        # Counter32, Gauge32, TimeTicks, Opaque, Counter64 all encode as integers.
        return _decode_int(data)
    if tag == _TAG_OCTET_STRING:
        # Brother strings are ASCII; decode permissively. Caller can re-decode bytes.
        try:
            return data.decode("ascii")
        except UnicodeDecodeError:
            return bytes(data)
    if tag == _TAG_NULL or tag == 0x80 or tag == 0x81 or tag == 0x82:
        # Null / noSuchObject / noSuchInstance / endOfMibView
        return None
    if tag == _TAG_OID:
        return _decode_oid(data)
    return bytes(data)


def _parse_response(packet: bytes, expected_request_id: int) -> dict[str, object]:
    """Parse a GetResponse PDU. Returns {oid: value}.

    Raises SnmpError on a non-zero error-status, malformed shape, or any
    structural inconsistency. IndexError from a malformed packet is converted
    to SnmpError so callers can rely on a single exception type.
    """
    try:
        return _parse_response_inner(packet, expected_request_id)
    except IndexError as e:
        raise SnmpError(f"malformed SNMP packet: {e}") from e


def _parse_response_inner(packet: bytes, expected_request_id: int) -> dict[str, object]:
    tag, body, _ = _decode_tlv(packet, 0)
    if tag != _TAG_SEQUENCE:
        raise SnmpError(f"top-level tag should be SEQUENCE, got 0x{tag:02x}")

    pos = 0
    _ver_tag, _ver, pos = _decode_tlv(body, pos)
    _comm_tag, _comm, pos = _decode_tlv(body, pos)
    pdu_tag, pdu, pos = _decode_tlv(body, pos)
    if pdu_tag != _TAG_GET_RESPONSE:
        raise SnmpError(f"expected GetResponse (0xA2), got 0x{pdu_tag:02x}")

    pos = 0
    _, rid_data, pos = _decode_tlv(pdu, pos)
    request_id = _decode_int(rid_data)
    if request_id != expected_request_id:
        raise SnmpError(f"request-id mismatch: sent {expected_request_id}, got {request_id}")

    _, err_status_data, pos = _decode_tlv(pdu, pos)
    err_status = _decode_int(err_status_data)
    _, _err_index_data, pos = _decode_tlv(pdu, pos)
    if err_status != 0:
        raise SnmpError(f"SNMP error-status {err_status} (see RFC 3416 §3 for codes)")

    _, varbinds, _ = _decode_tlv(pdu, pos)
    out: dict[str, object] = {}
    pos = 0
    while pos < len(varbinds):
        _, vb, pos = _decode_tlv(varbinds, pos)
        sub = 0
        _, oid_data, sub = _decode_tlv(vb, sub)
        val_tag, val_data, _ = _decode_tlv(vb, sub)
        out[_decode_oid(oid_data)] = _decode_value(val_tag, val_data)
    return out


# --- Public API -------------------------------------------------------------


def snmp_get(
    host: str,
    oid: str,
    *,
    community: str = _DEFAULT_COMMUNITY,
    port: int = _SNMP_PORT,
    timeout: float = _DEFAULT_TIMEOUT,
) -> object:
    """Issue a single SNMPv2c GET. Returns the decoded value or None for noSuchObject."""
    request_id = int.from_bytes(os.urandom(2), "big")
    packet = _build_get_request(oid, request_id, community)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(timeout)
    try:
        sock.sendto(packet, (host, port))
        data, _ = sock.recvfrom(4096)
    finally:
        sock.close()

    result = _parse_response(data, request_id)
    return result.get(oid)


# --- Brother-specific status builder ----------------------------------------

# Printer-MIB OIDs (RFC 3805). The Brother PT-P750W populates the human-
# readable Media Name string with values like "12mm(0.47\")" — that's the
# only place we get a clean tape-width number, since
# prtInputMediaDimXFeedDir on this firmware reports a sentinel (-2).
_OID_PRT_INPUT_MEDIA_NAME = "1.3.6.1.2.1.43.8.2.1.12.1.1"
_OID_PRT_CONSOLE_DISPLAY = "1.3.6.1.2.1.43.16.5.1.2.1.1"
# Host Resources MIB (RFC 2790) — the canonical printer error-state bit-flag
# field. Brother's prtAlertDescription table is mostly empty placeholders,
# but hrPrinterDetectedErrorState gives us cover-open / jam / no-media /
# offline as named bits, so we don't have to walk the alert table.
_OID_HRP_DETECTED_ERROR_STATE = "1.3.6.1.2.1.25.3.5.1.2.1"


# RFC 2790 hrPrinterDetectedErrorState bit assignments. Stored as
# (byte_index, bit_value) where bit_value is the BITS-style 0..15 index;
# bit-0 is the MSB of byte 0, bit-7 is its LSB, bit-8 is the MSB of byte 1.
_HRP_ERROR_BITS: tuple[tuple[int, int, str], ...] = (
    (0, 0x80, "low paper"),
    (0, 0x40, "no media"),
    (0, 0x20, "low toner"),
    (0, 0x10, "no toner"),
    (0, 0x08, "cover open"),
    (0, 0x04, "jam"),
    (0, 0x02, "offline"),
    (0, 0x01, "service requested"),
    (1, 0x80, "input tray missing"),
    (1, 0x40, "output tray missing"),
    (1, 0x20, "marker supply missing"),
    (1, 0x10, "output near full"),
    (1, 0x08, "output full"),
    (1, 0x04, "input tray empty"),
    (1, 0x02, "overdue preventive maintenance"),
)


def _to_octet_bytes(value: object) -> bytes:
    """SNMP OCTET STRING values come back as str when they're ASCII-clean,
    bytes when they aren't. BITS data is binary, so callers re-coerce here."""
    if isinstance(value, bytes):
        return value
    if isinstance(value, str):
        # Latin-1 is a 1:1 byte mapping — ASCII-clean strings round-trip.
        return value.encode("latin-1")
    return b""


def _decode_hrp_error_state(value: object) -> tuple[str, ...]:
    """Decode an hrPrinterDetectedErrorState BITS value into named errors."""
    raw = _to_octet_bytes(value)
    out: list[str] = []
    for byte_index, mask, name in _HRP_ERROR_BITS:
        if byte_index < len(raw) and raw[byte_index] & mask:
            out.append(name)
    return tuple(out)


class StatusViaSnmpFailed(RuntimeError):
    """Raised when the SNMP path can't produce a usable status snapshot."""


def _parse_media_width_mm(media_name: str) -> int:
    """Pull the leading mm number out of strings like ``'12mm(0.47\")'``.

    Returns the value in the same convention the printer reports over ESC i S
    (so :class:`TapeWidth` round-trips). Brother encodes 3.5mm tape as the
    sentinel ``4`` — this parser preserves that mapping.
    """
    import re
    match = re.match(r"\s*(\d+(?:\.\d+)?)", media_name)
    if not match:
        raise StatusViaSnmpFailed(
            f"could not parse a width from media name {media_name!r}"
        )
    val = float(match.group(1))
    # Brother reports 3.5mm tape as 4 in the ESC i S packet (see TapeWidth.MM_3_5).
    # Keep the SNMP path on the same convention so TapeWidth(...) maps cleanly.
    if val == 3.5:
        return 4
    return int(val)


def query_status_via_snmp(host: str, *, timeout: float = _DEFAULT_TIMEOUT):
    """Query the printer over SNMP and return a synthetic PrinterStatus.

    Importing PrinterStatus at call time keeps this module independent of
    the rest of the package — useful for unit-testing the SNMP layer alone.
    """
    from label_printer.constants import MediaType
    from label_printer.status import PrinterStatus

    try:
        media_name = snmp_get(host, _OID_PRT_INPUT_MEDIA_NAME, timeout=timeout)
        console = snmp_get(host, _OID_PRT_CONSOLE_DISPLAY, timeout=timeout)
        error_bits = snmp_get(host, _OID_HRP_DETECTED_ERROR_STATE, timeout=timeout)
    except (TimeoutError, OSError, SnmpError) as e:
        # SnmpError covers malformed packets, request-id mismatches, and any
        # non-zero error-status reply (e.g. noSuchName for an OID this firmware
        # doesn't populate). All three should fall back, not hard-fail.
        raise StatusViaSnmpFailed(f"SNMP query failed: {e}") from e

    if not isinstance(media_name, str) or not media_name:
        raise StatusViaSnmpFailed("printer reported no media name via SNMP")

    width_mm = _parse_media_width_mm(media_name)
    alerts = _decode_hrp_error_state(error_bits)

    # The console-text fallback only matters for printers that don't populate
    # hrPrinterDetectedErrorState — Brother does, so this just adds a string
    # like "PRINTING..." or "WAITING..." if the printer is mid-job.
    console_str = (console or "").strip() if isinstance(console, str) else ""
    if console_str and console_str.upper() != "READY" and not alerts:
        alerts = (console_str.lower(),)

    return PrinterStatus(
        # SNMP path: no underlying raster status packet, and the bit fields
        # would be a lie. has_error already covers the alerts tuple, and
        # describe_errors() prefers it over the bit fields.
        raw=b"",
        error_info_1=0,
        error_info_2=0,
        media_width_mm=width_mm,
        media_type=int(MediaType.LAMINATED_TAPE),
        mode=0,
        status_type=0,
        tape_color=0,
        text_color=0,
        alerts=alerts,
    )
