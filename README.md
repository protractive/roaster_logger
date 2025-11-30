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
- Install (venv 추천): `pip install -r requirements.txt`
- Run: `python -m ui.desktop.app`
- Features: multi-port start/stop, cycle info (bean/weight/note), live graph, logs tab, port editor (add/update/delete, COM 리스트 조회).
- 설정/로그 위치: `settings.toml`와 `logs/`는 사용자 프로필 디렉터리(appdirs 경로)에 자동 생성됨. 초기 실행 시 기본 설정이 만들어집니다.

## Build (onefile)
- Windows: `powershell -ExecutionPolicy Bypass -File scripts/build_win.ps1`
- macOS: `bash scripts/build_mac.sh`
- Linux: `bash scripts/build_linux.sh`
결과물은 `dist/` 폴더에 생성됩니다. (아이콘 파일이 없으면 기본 아이콘으로 빌드됨)
