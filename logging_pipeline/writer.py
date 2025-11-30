from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from logging_pipeline.schemas import LogRecord


class CycleLogWriter:
    """
    Simple line-delimited JSON writer for a cycle.
    File naming: {cycle_name}_{iso8601}.log
    """

    def __init__(self, base_dir: Path, cycle_name: str, started_at: datetime, file_prefix: str = "") -> None:
        self.base_dir = base_dir
        self.cycle_name = cycle_name
        self.started_at = started_at
        self.file_prefix = file_prefix
        self._file: Optional[Path] = None
        self._fh = None

    def __enter__(self) -> "CycleLogWriter":
        self.open()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def open(self) -> Path:
        self.base_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{self.file_prefix}{self.cycle_name}_{self.started_at.strftime('%Y%m%dT%H%M%S')}.log"
        self._file = self.base_dir / filename
        self._fh = self._file.open("a", encoding="utf-8")
        return self._file

    def write(self, record: LogRecord) -> None:
        if not self._fh:
            raise RuntimeError("Writer not opened")
        payload = {
            "ts": record.timestamp.isoformat(),
            "port_id": record.port_id,
            "data": record.payload,
            "meta": record.meta,
        }
        self._fh.write(json.dumps(payload, ensure_ascii=False) + "\n")
        self._fh.flush()

    def close(self) -> None:
        if self._fh:
            self._fh.close()
            self._fh = None
