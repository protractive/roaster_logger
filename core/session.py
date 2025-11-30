from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from logging_pipeline.schemas import LogRecord
from logging_pipeline.writer import CycleLogWriter


class Session:
    """Manage a single roasting cycle."""

    def __init__(
        self,
        cycle_name: str,
        log_dir: Path,
        record_writer_factory: Callable[[Path, str, datetime], CycleLogWriter],
    ) -> None:
        self.cycle_name = cycle_name
        self.log_dir = log_dir
        self.record_writer_factory = record_writer_factory
        self.started_at: Optional[datetime] = None
        self.writer: Optional[CycleLogWriter] = None

    def start(self) -> Path:
        if self.started_at:
            raise RuntimeError("Session already started")
        self.started_at = datetime.utcnow()
        self.writer = self.record_writer_factory(self.log_dir, self.cycle_name, self.started_at)
        return self.writer.open()

    def log(self, record: LogRecord) -> None:
        if not self.writer:
            raise RuntimeError("Session not started")
        self.writer.write(record)

    def stop(self) -> None:
        if self.writer:
            self.writer.close()
            self.writer = None
