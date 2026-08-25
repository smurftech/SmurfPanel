import threading

from pcpanel.device_service import DeviceService, DeviceState


class FakeReader:
    def __init__(
        self,
        *,
        on_event,
        stop_event,
        on_connected,
        on_disconnected,
        fail=False,
        stop_after_connect=False,
    ) -> None:
        self.on_event = on_event
        self.stop_event = stop_event
        self.on_connected = on_connected
        self.on_disconnected = on_disconnected
        self.fail = fail
        self.stop_after_connect = stop_after_connect
        self.last_error = None

    def start(self) -> None:
        if self.fail:
            self.last_error = "device unavailable"
            self.on_disconnected(self.last_error)
            return
        self.on_connected()
        if self.stop_after_connect:
            self.stop_event.set()
        self.on_disconnected(None)

    def join(self) -> None:
        return

    def send_output_report(self, payload: bytes) -> None:
        self.payload = payload


def test_device_service_reconnects_after_failed_open() -> None:
    stop_event = threading.Event()
    statuses = []
    attempts = 0

    def reader_factory(**kwargs):
        nonlocal attempts
        attempts += 1
        return FakeReader(
            **kwargs,
            fail=attempts == 1,
            stop_after_connect=attempts == 2,
        )

    service = DeviceService(
        on_event=lambda _event: None,
        stop_event=stop_event,
        on_state=statuses.append,
        reader_factory=reader_factory,
        reconnect_delay=0.01,
        max_reconnect_delay=0.01,
    )

    service.start()
    service.join(timeout=1)

    states = [status.state for status in statuses]
    assert attempts == 2
    assert states == [
        DeviceState.CONNECTING,
        DeviceState.DISCONNECTED,
        DeviceState.RECONNECTING,
        DeviceState.CONNECTED,
        DeviceState.STOPPED,
    ]
    assert statuses[1].message == "device unavailable"


def test_device_service_rejects_output_when_disconnected() -> None:
    service = DeviceService(
        on_event=lambda _event: None,
        stop_event=threading.Event(),
    )

    try:
        service.send_output_report(b"abc")
    except RuntimeError as exc:
        assert "not connected" in str(exc)
    else:
        raise AssertionError("Expected disconnected output report to fail")
