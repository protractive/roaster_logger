from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Any


@dataclass
class LogRecord:
    timestamp: datetime
    port_id: str
    payload: Dict[str, Any]
    meta: Dict[str, Any] = field(default_factory=dict)

