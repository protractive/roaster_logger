# roaster_logger

Project TODO and structure: see TODO.md and PROJECT_STRUCTURE.md.

## Quick start (stub client)
```
python app.py start-cycle --port-id roaster_1 --cycle-name test --iterations 3 --interval 0.5
```
- Settings file: config/settings.toml (per-port configs)
- Default client is an offline stub; use `--client pymodbus` with hardware (supports extra `client_params` in settings).
- Per-run overrides: `--timeout`, `--connect-retries`, `--read-retries` on `start-cycle`.

Logs are written to data/logs/ as `{cycle}_{timestamp}.log`.

## Manage ports (CRUD)
- List: `python app.py ports list`
- Add: `python app.py ports add --port-id new1 --device COM5 --baudrate 9600 --parity N --stopbits 1 --bytesize 8 --timeout 1.0 --unit-id 1`
- Update: `python app.py ports update --port-id roaster_1 --baudrate 19200 --connect-retries 5`
- Remove: `python app.py ports remove --port-id roaster_2`

## Session status/stop
- Status: `python app.py status` (shows active session via data/logs/.session.json)
- Stop: `python app.py stop` (clears session file; if a process is running, stop it manually/Ctrl+C)

## Desktop GUI (PySide6)
- Install: `pip install PySide6`
- Run: `python -m ui.desktop.app`
- Features: select port/client (stub or pymodbus), set cycle name/address/count/interval, start/stop logging; logs are saved to `data/logs/`.
