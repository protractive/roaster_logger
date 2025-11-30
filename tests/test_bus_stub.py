import pytest

from core.bus import ModbusBus, PortConfig, stub_client_factory


def test_read_retries_and_reconnect_stub():
    cfg = PortConfig(
        id="p1",
        device="COM1",
        baudrate=9600,
        parity="N",
        stopbits=1,
        bytesize=8,
        timeout=1.0,
        poll_interval=1.0,
        unit_id=1,
        connect_retries=1,
        read_retries=2,
        read_retry_delay=0.01,
    )
    bus = ModbusBus(cfg, client_factory=stub_client_factory)
    bus.connect()
    resp = bus.read_holding_registers(0, 3)
    assert resp["values"] == [0, 1, 2]


def test_connect_failure_propagates():
    class FailingClient:
        def __init__(self, **kwargs):
            pass

        def connect(self):
            return False

    cfg = PortConfig(
        id="p1",
        device="COM1",
        baudrate=9600,
        parity="N",
        stopbits=1,
        bytesize=8,
        timeout=1.0,
        poll_interval=1.0,
        unit_id=1,
    )
    bus = ModbusBus(cfg, client_factory=lambda **kwargs: FailingClient())
    with pytest.raises(ConnectionError):
        bus.connect()
