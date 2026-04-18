"""Transport protocol.

Transports accept a fully-encoded byte stream from `encode_job()` and put
it in front of the printer (or into a file, for dry runs).
"""

from __future__ import annotations

from typing import Protocol


class Transport(Protocol):
    name: str

    def send(self, data: bytes) -> None: ...
