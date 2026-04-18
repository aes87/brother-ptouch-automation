"""Transport protocol.

Transports accept a fully-encoded byte stream from :func:`encode_job` /
:func:`encode_batch` and put it in front of the printer (or into a file,
for dry runs). Real transports (USB, Bluetooth) additionally support
``query_status()`` so callers can verify what's loaded before printing.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from label_printer.status import PrinterStatus


class StatusUnavailable(RuntimeError):
    """Raised by transports that cannot query status (e.g. DryRun, offline)."""


@runtime_checkable
class Transport(Protocol):
    name: str

    def send(self, data: bytes) -> None: ...


@runtime_checkable
class StatusAwareTransport(Transport, Protocol):
    """A transport that can round-trip a status-request command."""

    def query_status(self) -> PrinterStatus: ...
