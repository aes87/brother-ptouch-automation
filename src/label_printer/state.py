"""Persisted user state: last-selected tape, last transport."""

from __future__ import annotations

import os
import tomllib
from dataclasses import asdict, dataclass
from pathlib import Path

from label_printer.tape import TapeWidth

_CONFIG_DIR = Path(
    os.environ.get("LABEL_PRINTER_CONFIG_DIR")
    or (Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config") / "label-printer")
)
_STATE_FILE = _CONFIG_DIR / "state.toml"


@dataclass
class State:
    tape_mm: int = 12

    def tape(self) -> TapeWidth:
        return TapeWidth(self.tape_mm if self.tape_mm != 3 else 4)


def load() -> State:
    if not _STATE_FILE.exists():
        return State()
    with _STATE_FILE.open("rb") as f:
        data = tomllib.load(f)
    return State(**{k: v for k, v in data.items() if k in State.__dataclass_fields__})


def save(state: State) -> Path:
    _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    lines = [f"{k} = {v!r}" for k, v in asdict(state).items()]
    _STATE_FILE.write_text("\n".join(lines) + "\n")
    return _STATE_FILE
