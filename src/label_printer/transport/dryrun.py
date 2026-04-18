"""File-backed transport. Writes raster command bytes to disk for inspection.

Every pre-hardware phase uses this transport. Once real USB / BT transports
land, DryRunTransport remains useful for goldens, CI, and preview workflows.
"""

from __future__ import annotations

from pathlib import Path


class DryRunTransport:
    name = "dryrun"

    def __init__(self, out_path: str | Path):
        self.out_path = Path(out_path)
        self.out_path.parent.mkdir(parents=True, exist_ok=True)

    def send(self, data: bytes) -> None:
        self.out_path.write_bytes(data)

    def hex_preview(self, data: bytes, line_limit: int = 8) -> str:
        """Return a short hex summary for stdout feedback."""
        header = f"{len(data)} bytes → {self.out_path}"
        hex_line = " ".join(f"{b:02x}" for b in data[: line_limit * 16])
        wrapped = "\n".join(
            hex_line[i : i + 48] for i in range(0, len(hex_line), 48)
        )
        return f"{header}\n{wrapped}"
