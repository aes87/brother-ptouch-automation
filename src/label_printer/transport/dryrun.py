"""File-backed transport. Writes raster command bytes to disk for inspection.

Every pre-hardware phase uses this transport. Once real USB / BT transports
land, DryRunTransport remains useful for goldens, CI, and preview workflows.
It also supports a synthetic ``query_status()`` for tests that exercise
status-aware code paths without hardware.
"""

from __future__ import annotations

from pathlib import Path

from label_printer.status import PrinterStatus, build_mock_status, parse_status
from label_printer.transport.base import StatusUnavailable


class DryRunTransport:
    name = "dryrun"

    def __init__(self, out_path: str | Path, mock_status: bytes | None = None):
        self.out_path = Path(out_path)
        self.out_path.parent.mkdir(parents=True, exist_ok=True)
        # Optional: tests can inject a synthetic status packet; default is
        # "no printer attached" (raises on query) unless mock_status is set.
        self._mock_status = mock_status

    def send(self, data: bytes) -> None:
        self.out_path.write_bytes(data)

    def query_status(self) -> PrinterStatus:
        if self._mock_status is None:
            raise StatusUnavailable(
                "DryRunTransport has no mock status; pass mock_status=... to construct one"
            )
        return parse_status(self._mock_status)

    def hex_preview(self, data: bytes, line_limit: int = 8) -> str:
        """Return a short hex summary for stdout feedback."""
        header = f"{len(data)} bytes → {self.out_path}"
        hex_line = " ".join(f"{b:02x}" for b in data[: line_limit * 16])
        wrapped = "\n".join(
            hex_line[i : i + 48] for i in range(0, len(hex_line), 48)
        )
        return f"{header}\n{wrapped}"


def mock_dryrun_with_tape(out_path: str | Path, tape_mm: int = 12) -> DryRunTransport:
    """Convenience factory for tests: a dry-run transport that reports `tape_mm` tape loaded."""
    return DryRunTransport(out_path, mock_status=build_mock_status(media_width_mm=tape_mm))
