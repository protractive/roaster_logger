from datetime import datetime
from pathlib import Path
import json
import tempfile

from logging_pipeline.schemas import LogRecord
from logging_pipeline.writer import CycleLogWriter


def test_cycle_log_writer_creates_file_and_writes_jsonl():
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)
        ts = datetime(2024, 1, 1, 12, 0, 0)
        writer = CycleLogWriter(base, "cycle1", ts)
        path = writer.open()

        record = LogRecord(timestamp=ts, port_id="p1", payload={"val": 123}, meta={"m": 1})
        writer.write(record)
        writer.close()

        assert path.exists()
        content = path.read_text(encoding="utf-8").strip().splitlines()
        assert len(content) == 1
        data = json.loads(content[0])
        assert data["port_id"] == "p1"
        assert data["data"]["val"] == 123
        assert data["meta"]["m"] == 1
        assert "cycle1" in path.name
        assert path.name.endswith(".log")
