from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, Callable, Optional

log = logging.getLogger("bus")


@dataclass
class PortConfig:
    id: str
    device: str
    baudrate: int
    parity: str
    stopbits: int
    bytesize: int
    timeout: float
    poll_interval: float
    unit_id: int
    register_map: str = "default"
    read_address: int = 0
    read_count: int = 1
    value_index: int = 0
    enabled: bool = True
    connect_retries: int = 3
    connect_retry_delay: float = 1.0
    read_retries: int = 1
    read_retry_delay: float = 0.2
    reconnect_on_read_error: bool = True
    client_params: Dict[str, Any] = None  # extra kwargs for real clients


class ModbusBus:
    """
    Thin wrapper around a Modbus RTU client.
    The actual client library (e.g., pymodbus) is injected to keep deps optional.
    """

    def __init__(self, config: PortConfig, client_factory: Callable[..., Any]) -> None:
        self.config = config
        self._client_factory = client_factory
        self._client: Any = None

    def connect(self) -> None:
        """Instantiate and open the client."""
        attempts = max(1, self.config.connect_retries)
        last_exc: Exception | None = None
        for attempt in range(1, attempts + 1):
            try:
                kwargs = {
                    "method": "rtu",
                    "port": self.config.device,
                    "baudrate": self.config.baudrate,
                    "parity": self.config.parity,
                    "stopbits": self.config.stopbits,
                    "bytesize": self.config.bytesize,
                    "timeout": self.config.timeout,
                }
                if self.config.client_params:
                    kwargs.update(self.config.client_params)
                try:
                    self._client = self._client_factory(**kwargs)
                except TypeError as type_exc:
                    if self.config.client_params:
                        log.warning(
                            "Client factory rejected extra params %s: %s; retrying with base params only",
                            list(self.config.client_params.keys()),
                            type_exc,
                        )
                        base_keys = ("port", "baudrate", "parity", "stopbits", "bytesize", "timeout", "method")
                        filtered = {k: v for k, v in kwargs.items() if k in base_keys}
                        self._client = self._client_factory(**filtered)
                    else:
                        raise
                if hasattr(self._client, "connect"):
                    if not self._client.connect():
                        raise ConnectionError(f"Failed to connect to {self.config.device}")
                return
            except Exception as exc:
                last_exc = exc
                if attempt >= attempts:
                    log.error(
                        "Connect failed after %s attempt(s) for %s: %s",
                        attempts,
                        self.config.device,
                        exc,
                    )
                    raise
                log.debug("Connect attempt %s/%s failed for %s: %s", attempt, attempts, self.config.device, exc)
                time.sleep(self.config.connect_retry_delay)
        if last_exc:
            raise last_exc

    def close(self) -> None:
        if self._client and hasattr(self._client, "close"):
            self._client.close()

    def read_holding_registers(self, address: int, count: int) -> Any:
        """Read holding registers; caller interprets payload."""
        if not self._client:
            raise RuntimeError("Client not connected")
        if not hasattr(self._client, "read_holding_registers"):
            raise RuntimeError("Client does not implement read_holding_registers")

        attempts = max(1, self.config.read_retries)
        last_exc: Exception | None = None
        for attempt in range(1, attempts + 1):
            try:
                resp = _call_read_holding(
                    self._client.read_holding_registers,
                    address=address,
                    count=count,
                    unit_id=self.config.unit_id,
                )
                if hasattr(resp, "isError") and callable(resp.isError) and resp.isError():
                    raise IOError(f"Modbus error response: {resp}")
                return resp
            except Exception as exc:
                last_exc = exc
                if attempt >= attempts:
                    log.error(
                        "Read failed after %s attempt(s) on %s: %s",
                        attempts,
                        self.config.device,
                        exc,
                    )
                    raise
                log.debug("Read attempt %s/%s failed on %s: %s", attempt, attempts, self.config.device, exc)
                if self.config.reconnect_on_read_error:
                    try:
                        self.close()
                        self.connect()
                    except Exception as conn_exc:  # noqa: BLE001
                        log.error("Reconnect failed: %s", conn_exc)
                        if attempt >= attempts:
                            raise
                time.sleep(self.config.read_retry_delay)
        if last_exc:
            raise last_exc


def load_port_configs(raw_settings: Dict[str, Any]) -> Dict[str, PortConfig]:
    """Build PortConfig objects keyed by id."""
    ports: Dict[str, PortConfig] = {}
    for entry in raw_settings.get("ports", []):
        cfg = PortConfig(
            id=entry["id"],
            device=entry["device"],
            baudrate=int(entry["baudrate"]),
            parity=str(entry["parity"]),
            stopbits=int(entry["stopbits"]),
            bytesize=int(entry["bytesize"]),
            timeout=float(entry["timeout"]),
            poll_interval=float(entry.get("poll_interval", 1.0)),
            unit_id=int(entry["unit_id"]),
            register_map=entry.get("register_map", "default"),
            read_address=int(entry.get("read_address", 0)),
            read_count=int(entry.get("read_count", 1)),
            value_index=int(entry.get("value_index", 0)),
            enabled=bool(entry.get("enabled", True)),
            connect_retries=int(entry.get("connect_retries", 3)),
            connect_retry_delay=float(entry.get("connect_retry_delay", 1.0)),
            read_retries=int(entry.get("read_retries", 1)),
            read_retry_delay=float(entry.get("read_retry_delay", 0.2)),
            reconnect_on_read_error=bool(entry.get("reconnect_on_read_error", True)),
            client_params=entry.get("client_params") or {},
        )
        ports[cfg.id] = cfg
    return ports


class _StubModbusClient:
    """Offline stub client to allow CLI testing without hardware."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.connected = False
        self._counter = 0

    def connect(self) -> bool:
        self.connected = True
        return True

    def close(self) -> None:
        self.connected = False

    def read_holding_registers(self, address: int, count: int, unit: int) -> Dict[str, Any]:
        # Simulate changing register values
        self._counter += 1
        data = list(range(address, address + count))
        return {"address": address, "count": count, "unit": unit, "values": data, "sample": self._counter}


def stub_client_factory(**kwargs: Any) -> _StubModbusClient:
    """Factory that returns the stub client."""
    return _StubModbusClient(**kwargs)


def pymodbus_client_factory(**kwargs: Any) -> Any:
    """Factory that returns a pymodbus serial client."""
    try:
        from pymodbus.client import ModbusSerialClient
    except Exception as exc:  # pragma: no cover - optional dependency
        raise RuntimeError("pymodbus is not installed") from exc
    kwargs.pop("method", None)  # pymodbus>=3 does not accept 'method'
    return ModbusSerialClient(**kwargs)


def _call_read_holding(func: Callable[..., Any], address: int, count: int, unit_id: int) -> Any:
    """
    Call read_holding_registers with signature detection across pymodbus versions.
    Tries unit/slave keyword; falls back to count-only if unit not supported.
    """
    try:
        import inspect
    except Exception:
        return func(address, count, unit=unit_id)

    sig = inspect.signature(func)
    params = sig.parameters
    kwargs: Dict[str, Any] = {}
    if "count" in params:
        kwargs["count"] = count
    if "unit" in params:
        kwargs["unit"] = unit_id
    elif "slave" in params:
        kwargs["slave"] = unit_id
    try:
        return func(address, **kwargs)
    except TypeError:
        # Retry without unit/slave if not accepted
        kwargs.pop("unit", None)
        kwargs.pop("slave", None)
        try:
            return func(address, **kwargs)
        except TypeError:
            # Last resort: positional address + count
            return func(address, count)
