"""TCP transport for Wi-Fi / Ethernet-attached Brother printers.

Brother network printers expose the raster command stream on TCP port 9100
(the standard "JetDirect" / "raw" print port). The protocol is identical to
USB — we just carry it over a socket.

Status queries do *not* go over the print socket: Brother firmware treats
TCP:9100 as write-only, silently swallowing ``ESC i S``. SNMP on UDP:161 is
the documented out-of-band path; see :func:`query_status_via_snmp`.
"""

from __future__ import annotations

import socket

from label_printer.status import PrinterStatus
from label_printer.transport.base import StatusAwareTransport, StatusUnavailable

DEFAULT_PORT = 9100
_DEFAULT_CONNECT_TIMEOUT = 5.0
_DEFAULT_RECV_TIMEOUT = 10.0


class NetworkTransport(StatusAwareTransport):
    """Talks to a Brother printer over TCP:9100, with SNMP for status."""

    name = "network"

    def __init__(
        self,
        host: str,
        port: int = DEFAULT_PORT,
        *,
        connect_timeout: float = _DEFAULT_CONNECT_TIMEOUT,
        recv_timeout: float = _DEFAULT_RECV_TIMEOUT,
    ):
        self.host = host
        self.port = port
        self.connect_timeout = connect_timeout
        self.recv_timeout = recv_timeout

    def _connect(self) -> socket.socket:
        s = socket.create_connection((self.host, self.port), timeout=self.connect_timeout)
        s.settimeout(self.recv_timeout)
        return s

    def probe(self, timeout: float = 3.0) -> None:
        """Open and immediately close a socket to verify the printer accepts connections.

        Raises OSError on connect failure. Used by ``lp scan`` to check
        reachability without sending any payload.
        """
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        try:
            s.connect((self.host, self.port))
        finally:
            s.close()

    def send(self, data: bytes) -> None:
        with self._connect() as s:
            s.sendall(data)

    def query_status(self) -> PrinterStatus:
        """Query status over SNMP (UDP:161). Raises StatusUnavailable on failure.

        TCP:9100 is *not* used — Brother network firmware treats it as
        write-only and ``ESC i S`` never returns. The Printer MIB on UDP:161
        is the documented escape hatch and exposes the loaded tape width via
        ``prtInputMediaName`` plus the canonical error bits via
        ``hrPrinterDetectedErrorState``. If SNMP is disabled on the printer,
        we surface :class:`StatusUnavailable` so callers can soften their
        pre-print tape check.
        """
        from label_printer.transport.snmp import (
            StatusViaSnmpFailed,
            query_status_via_snmp,
        )

        try:
            return query_status_via_snmp(self.host)
        except StatusViaSnmpFailed as e:
            raise StatusUnavailable(str(e)) from e
