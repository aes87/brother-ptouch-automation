"""Unit tests for the hand-rolled SNMP v2c client.

We don't fake an SNMP server — the value of these tests is in pinning the
ASN.1 BER encoding (which is fiddly) and the media-name parser (which has
to handle Brother's "12mm(0.47\")" formatting).
"""

from __future__ import annotations

import pytest

from label_printer.transport.snmp import (
    StatusViaSnmpFailed,
    _build_get_request,
    _enc_int,
    _enc_oid,
    _parse_media_width_mm,
    _parse_response,
)

# --- ASN.1 BER encoding -----------------------------------------------------


def test_enc_oid_round_trips_known_examples():
    # 1.3.6.1.2.1.1.1.0 — the canonical sysDescr OID.
    # Expected: tag 0x06, length 0x08, body 2b 06 01 02 01 01 01 00
    out = _enc_oid("1.3.6.1.2.1.1.1.0")
    assert out == bytes.fromhex("06082b06010201010100")


def test_enc_oid_handles_multi_byte_arc():
    # Arc 8072 = 63·128 + 8 → base-128 bytes 0xBF 0x08 (high bit on first only).
    # 1.3.6.1.4.1.8072 → 06 08 2b 06 01 04 01 bf 08
    out = _enc_oid("1.3.6.1.4.1.8072")
    assert out == bytes.fromhex("06072b06010401bf08")


def test_enc_int_zero_one_negative_large():
    assert _enc_int(0) == bytes.fromhex("020100")
    assert _enc_int(1) == bytes.fromhex("020101")
    assert _enc_int(-1) == bytes.fromhex("0201ff")
    # 256 needs two bytes with a leading 0x00 to keep it positive in two's complement.
    assert _enc_int(256) == bytes.fromhex("02020100")


def test_build_get_request_round_trip_via_parser():
    """Round-trip: encode a request, then parse it as if it were a response.

    Tags differ (Request 0xA0 vs Response 0xA2) so we can't truly round-trip,
    but we can confirm the encoder produces well-formed ASN.1 by parsing the
    inner pieces ourselves.
    """
    packet = _build_get_request("1.3.6.1.2.1.1.1.0", request_id=0x1234,
                                community="public")

    # Top-level tag must be SEQUENCE (0x30).
    assert packet[0] == 0x30
    # Some sanity: the OID and "public" string must appear in the payload.
    assert b"public" in packet
    assert bytes.fromhex("06082b06010201010100") in packet


# --- Response parser --------------------------------------------------------


def _build_synthetic_response(oid: str, value_tlv: bytes, request_id: int) -> bytes:
    """Build a complete GetResponse packet with a single varbind."""
    from label_printer.transport.snmp import (
        _enc_octet_string,
        _enc_sequence,
        _tlv,
    )

    varbind = _enc_sequence(_enc_oid(oid), value_tlv)
    varbinds = _enc_sequence(varbind)
    pdu = _tlv(
        0xA2,  # GetResponse
        _enc_int(request_id) + _enc_int(0) + _enc_int(0) + varbinds,
    )
    return _enc_sequence(_enc_int(1), _enc_octet_string(b"public"), pdu)


def test_parse_response_extracts_octet_string():
    from label_printer.transport.snmp import _enc_octet_string
    oid = "1.3.6.1.2.1.43.8.2.1.12.1.1"
    payload = _build_synthetic_response(oid, _enc_octet_string(b"12mm(0.47\")"),
                                        request_id=0xBEEF)
    result = _parse_response(payload, expected_request_id=0xBEEF)
    assert result == {oid: '12mm(0.47")'}


def test_parse_response_extracts_integer():
    from label_printer.transport.snmp import _enc_int as enc_int
    oid = "1.3.6.1.2.1.43.8.2.1.3.1.1"
    payload = _build_synthetic_response(oid, enc_int(3), request_id=42)
    result = _parse_response(payload, expected_request_id=42)
    assert result == {oid: 3}


def test_parse_response_rejects_request_id_mismatch():
    from label_printer.transport.snmp import _enc_int as enc_int
    oid = "1.3.6.1.2.1.1.3.0"
    payload = _build_synthetic_response(oid, enc_int(0), request_id=1)
    from label_printer.transport.snmp import SnmpError
    with pytest.raises(SnmpError, match="request-id mismatch"):
        _parse_response(payload, expected_request_id=999)


# --- Media-name parser ------------------------------------------------------


@pytest.mark.parametrize(
    "name,expected",
    [
        ('12mm(0.47")', 12),
        ('24mm(0.94")', 24),
        ("9mm", 9),
        # Brother reports 3.5mm tape as 4 in the ESC i S packet — TapeWidth.MM_3_5
        # has value 4 to match. The SNMP parser maps the human "3.5mm" string back
        # to the same 4 so TapeWidth(width) round-trips on either path.
        ("3.5mm", 4),
        ('3.5mm(0.14")', 4),
    ],
)
def test_parse_media_width_matches_tapewidth_convention(name: str, expected: int):
    assert _parse_media_width_mm(name) == expected


def test_parse_media_width_rejects_garbage():
    with pytest.raises(StatusViaSnmpFailed):
        _parse_media_width_mm("no-media")


# --- hrPrinterDetectedErrorState bit decoder --------------------------------


def test_decode_hrp_no_errors():
    from label_printer.transport.snmp import _decode_hrp_error_state
    assert _decode_hrp_error_state(b"\x00\x00") == ()
    assert _decode_hrp_error_state("\x00") == ()
    assert _decode_hrp_error_state("") == ()


def test_decode_hrp_named_bits():
    from label_printer.transport.snmp import _decode_hrp_error_state
    # Cover open (byte 0, bit 0x08).
    assert _decode_hrp_error_state(b"\x08") == ("cover open",)
    # No media (byte 0, bit 0x40) + jam (byte 0, bit 0x04) — co-occurring.
    assert _decode_hrp_error_state(b"\x44") == ("no media", "jam")
    # Input tray empty lives in byte 1.
    assert _decode_hrp_error_state(b"\x00\x04") == ("input tray empty",)


def test_decode_hrp_handles_str_input():
    """SNMP OCTET STRING values come back as str when ASCII-clean — must coerce."""
    from label_printer.transport.snmp import _decode_hrp_error_state
    # Byte 0 = 0x08 = ASCII backspace, decodes as a string.
    assert _decode_hrp_error_state("\x08") == ("cover open",)
