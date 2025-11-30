from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class SessionState:
    cycle_name: str
    port_id: str
    started_at: str  # ISO format
    log_file: str

    @classmethod
    def from_json(cls, text: str) -> "SessionState":
        data = json.loads(text)
        return cls(**data)

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, indent=2)


class SessionTracker:
    """
    File-based session tracker to allow stop/status commands.
    Not concurrency-safe for multiple processes; simple for single-instance CLI use.
    """

    def __init__(self, state_file: Path) -> None:
        self.state_file = state_file

    def save(self, state: SessionState) -> None:
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(state.to_json(), encoding="utf-8")

    def clear(self) -> None:
        if self.state_file.exists():
            self.state_file.unlink()

    def load(self) -> Optional[SessionState]:
        if not self.state_file.exists():
            return None
        return SessionState.from_json(self.state_file.read_text(encoding="utf-8"))
