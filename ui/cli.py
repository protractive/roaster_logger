from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict

from config import add_or_update_port, get_port, load_settings, remove_port, save_settings
from core.bus import ModbusBus, load_port_configs, stub_client_factory, pymodbus_client_factory
from core.session import Session
from core.session_state import SessionTracker, SessionState
from logging_pipeline.schemas import LogRecord
from logging_pipeline.writer import CycleLogWriter

log = logging.getLogger("cli")


def _resolve_client_factory(name: str) -> Callable[..., Any]:
    if name == "stub":
        return stub_client_factory
    if name == "pymodbus":
        return pymodbus_client_factory
    raise ValueError(f"Unknown client '{name}'")


def start_cycle(args: argparse.Namespace) -> None:
    settings = load_settings(args.settings)
    ports = load_port_configs(settings)
    if args.port_id not in ports:
        raise SystemExit(f"Port id '{args.port_id}' not found. Available: {', '.join(ports.keys())}")

    port_cfg = ports[args.port_id]
    if hasattr(port_cfg, "enabled") and not port_cfg.enabled:
        raise SystemExit(f"Port id '{args.port_id}' is disabled in settings.")
    if args.timeout is not None:
        port_cfg.timeout = args.timeout
    if args.connect_retries is not None:
        port_cfg.connect_retries = args.connect_retries
    if args.read_retries is not None:
        port_cfg.read_retries = args.read_retries
    client_factory = _resolve_client_factory(args.client)

    bus = ModbusBus(port_cfg, client_factory=client_factory)
    bus.connect()

    log_dir = Path(settings["app"]["log_dir"])
    state_file = log_dir / ".session.json"
    tracker = SessionTracker(state_file)
    existing = tracker.load()
    if existing:
        raise SystemExit(f"Session already running: {existing.cycle_name} on {existing.port_id}, started {existing.started_at}")

    session = Session(
        cycle_name=args.cycle_name,
        log_dir=log_dir,
        record_writer_factory=lambda base_dir, name, ts: CycleLogWriter(base_dir, name, ts),
    )
    log.info("Starting cycle '%s' on port '%s'", args.cycle_name, port_cfg.id)
    log_path = session.start()
    tracker.save(
        SessionState(
            cycle_name=args.cycle_name,
            port_id=port_cfg.id,
            started_at=session.started_at.isoformat() if session.started_at else "",
            log_file=str(log_path),
        )
    )

    try:
        for i in range(args.iterations):
            resp = bus.read_holding_registers(args.address, args.count)
            record = LogRecord(
                timestamp=datetime.utcnow(),
                port_id=port_cfg.id,
                payload={"holding_registers": _serialize_modbus_response(resp)},
                meta={"iteration": i},
            )
            session.log(record)
            log.debug("Logged iteration %s: %s", i, resp)
            time.sleep(args.interval)
    except KeyboardInterrupt:
        log.info("Interrupted, closing session.")
    finally:
        session.stop()
        tracker.clear()
        bus.close()
        log.info("Session finished. Log written to '%s'", log_dir)


def ports_list(args: argparse.Namespace) -> None:
    settings = load_settings(args.settings)
    ports = settings.get("ports", [])
    if not ports:
        print("No ports configured.")
        return
    for p in ports:
        print(f"{p['id']}: {p['device']} baud={p['baudrate']} parity={p['parity']} stopbits={p['stopbits']} bytesize={p['bytesize']} unit_id={p['unit_id']}")


def _collect_port_data(args: argparse.Namespace) -> Dict[str, Any]:
    fields = [
        ("id", "port_id"),
        ("device", "device"),
        ("baudrate", "baudrate"),
        ("parity", "parity"),
        ("stopbits", "stopbits"),
        ("bytesize", "bytesize"),
        ("timeout", "timeout"),
        ("poll_interval", "poll_interval"),
        ("unit_id", "unit_id"),
        ("register_map", "register_map"),
        ("connect_retries", "connect_retries"),
        ("connect_retry_delay", "connect_retry_delay"),
        ("read_retries", "read_retries"),
        ("read_retry_delay", "read_retry_delay"),
    ]
    data: Dict[str, Any] = {}
    for dest_key, arg_key in fields:
        val = getattr(args, arg_key, None)
        if val is not None:
            data[dest_key] = val
    return data


def ports_add(args: argparse.Namespace) -> None:
    settings = load_settings(args.settings)
    data = _collect_port_data(args)
    action, _ = add_or_update_port(settings, data)
    save_settings(settings, args.settings)
    log.info("Port %s %s", data["id"], action)


def ports_update(args: argparse.Namespace) -> None:
    settings = load_settings(args.settings)
    existing = get_port(settings, args.port_id)
    if not existing:
        raise SystemExit(f"Port id '{args.port_id}' not found.")
    data = existing.copy()
    data.update(_collect_port_data(args))
    action, _ = add_or_update_port(settings, data)
    save_settings(settings, args.settings)
    log.info("Port %s %s", data["id"], action)


def ports_remove(args: argparse.Namespace) -> None:
    settings = load_settings(args.settings)
    removed = remove_port(settings, args.port_id)
    if not removed:
        raise SystemExit(f"Port id '{args.port_id}' not found.")
    save_settings(settings, args.settings)
    log.info("Port %s removed", args.port_id)


def show_status(args: argparse.Namespace) -> None:
    settings = load_settings(args.settings)
    log_dir = Path(settings["app"]["log_dir"])
    tracker = SessionTracker(log_dir / ".session.json")
    state = tracker.load()
    if not state:
        print("No active session.")
        return
    print(
        f"Active session: cycle={state.cycle_name}, port={state.port_id}, started={state.started_at}, log_file={state.log_file}"
    )


def stop_session(args: argparse.Namespace) -> None:
    settings = load_settings(args.settings)
    log_dir = Path(settings["app"]["log_dir"])
    tracker = SessionTracker(log_dir / ".session.json")
    state = tracker.load()
    if not state:
        print("No active session.")
        return
    # Best-effort stop: currently only clears the tracker file.
    tracker.clear()
    print(f"Cleared session state for cycle={state.cycle_name}. If process is running, stop it manually (Ctrl+C).")


def _serialize_modbus_response(resp: Any) -> Any:
    """Best-effort JSON-serializable view of a pymodbus response."""
    if resp is None:
        return None
    if hasattr(resp, "registers"):
        return {"registers": getattr(resp, "registers")}
    if hasattr(resp, "bits"):
        return {"bits": getattr(resp, "bits")}
    try:
        # simple types pass through
        import json

        json.dumps(resp)
        return resp
    except Exception:
        return repr(resp)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Roaster logger CLI")
    parser.add_argument("--settings", default="config/settings.toml", help="Path to settings TOML")
    sub = parser.add_subparsers(dest="command", required=True)

    start = sub.add_parser("start-cycle", help="Start a logging cycle")
    start.add_argument("--port-id", required=True, help="Port id defined in settings.toml")
    start.add_argument("--cycle-name", required=True, help="Cycle name for the log filename")
    start.add_argument("--iterations", type=int, default=5, help="Number of reads to perform")
    start.add_argument("--interval", type=float, default=1.0, help="Seconds between reads")
    start.add_argument("--address", type=int, default=0, help="Register start address")
    start.add_argument("--count", type=int, default=10, help="Number of registers to read")
    start.add_argument("--client", choices=["stub", "pymodbus"], default="stub", help="Modbus client backend")
    start.add_argument("--timeout", type=float, help="Override port timeout for this run (seconds)")
    start.add_argument("--connect-retries", type=int, dest="connect_retries", help="Override connect retry count")
    start.add_argument("--read-retries", type=int, dest="read_retries", help="Override read retry count")
    start.set_defaults(func=start_cycle)

    ports = sub.add_parser("ports", help="Manage port configurations (CRUD)")
    ports_sub = ports.add_subparsers(dest="ports_cmd", required=True)

    ports_list_cmd = ports_sub.add_parser("list", help="List configured ports")
    ports_list_cmd.set_defaults(func=ports_list)

    def add_port_args(cmd: argparse.ArgumentParser, require_all: bool) -> None:
        cmd.add_argument("--port-id", required=True, help="Unique port id")
        cmd.add_argument("--device", required=require_all, help="Device path, e.g., COM3 or /dev/ttyUSB0")
        cmd.add_argument("--baudrate", type=int, required=require_all)
        cmd.add_argument("--parity", choices=["N", "E", "O"], required=require_all)
        cmd.add_argument("--stopbits", type=int, required=require_all)
        cmd.add_argument("--bytesize", type=int, required=require_all)
        cmd.add_argument("--timeout", type=float, required=require_all)
        cmd.add_argument("--poll-interval", type=float, dest="poll_interval")
        cmd.add_argument("--unit-id", type=int, required=require_all)
        cmd.add_argument("--register-map", dest="register_map")
        cmd.add_argument("--connect-retries", type=int, dest="connect_retries")
        cmd.add_argument("--connect-retry-delay", type=float, dest="connect_retry_delay")
        cmd.add_argument("--read-retries", type=int, dest="read_retries")
        cmd.add_argument("--read-retry-delay", type=float, dest="read_retry_delay")

    ports_add_cmd = ports_sub.add_parser("add", help="Add a new port")
    add_port_args(ports_add_cmd, require_all=True)
    ports_add_cmd.set_defaults(func=ports_add)

    ports_update_cmd = ports_sub.add_parser("update", help="Update an existing port")
    add_port_args(ports_update_cmd, require_all=False)
    ports_update_cmd.set_defaults(func=ports_update)

    ports_rm_cmd = ports_sub.add_parser("remove", help="Remove a port by id")
    ports_rm_cmd.add_argument("--port-id", required=True, help="Port id to remove")
    ports_rm_cmd.set_defaults(func=ports_remove)

    status = sub.add_parser("status", help="Show active session if any")
    status.set_defaults(func=show_status)

    stop = sub.add_parser("stop", help="Clear active session state (manual process stop may still be needed)")
    stop.set_defaults(func=stop_session)
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    try:
        args.func(args)
    except KeyboardInterrupt:
        log.info("Interrupted by user.")
        sys.exit(130)
    except Exception as exc:  # noqa: BLE001
        log.error("%s", exc, exc_info=bool(os.environ.get("DEBUG")))
        sys.exit(1)


if __name__ == "__main__":
    main()
