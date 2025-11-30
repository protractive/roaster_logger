from pathlib import Path
import tempfile

from config import add_or_update_port, load_settings, remove_port, save_settings


def test_add_update_remove_port_roundtrip():
    base = {
        "app": {"name": "x", "env": "local", "log_dir": "data/logs"},
        "logging": {"level": "INFO"},
        "ports": [],
    }
    with tempfile.TemporaryDirectory() as tmpdir:
        settings_path = Path(tmpdir) / "settings.toml"
        save_settings(base, settings_path)

        # add
        action, port = add_or_update_port(
            base,
            {
                "id": "p1",
                "device": "COM1",
                "baudrate": 9600,
                "parity": "N",
                "stopbits": 1,
                "bytesize": 8,
                "timeout": 1.0,
                "poll_interval": 1.0,
                "unit_id": 1,
            },
        )
        assert action == "added"
        save_settings(base, settings_path)

        loaded = load_settings(settings_path)
        assert loaded["ports"][0]["id"] == "p1"

        # update
        action, port = add_or_update_port(
            loaded,
            {
                "id": "p1",
                "baudrate": 19200,
                "connect_retries": 5,
            },
        )
        assert action == "updated"
        assert port["baudrate"] == 19200
        assert port["connect_retries"] == 5

        # remove
        removed = remove_port(loaded, "p1")
        assert removed
        save_settings(loaded, settings_path)
        loaded2 = load_settings(settings_path)
        assert loaded2["ports"] == []
