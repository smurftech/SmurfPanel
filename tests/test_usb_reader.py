import threading

from pcpanel.usb_reader import PyUsbReader


class FlakyReader(PyUsbReader):
    def __init__(self, stop_event, statuses):
        super().__init__(
            on_event=lambda _event: None,
            stop_event=stop_event,
            on_status=statuses.append,
        )
        self.open_attempts = 0

    def _open_endpoint(self):
        self.open_attempts += 1
        if self.open_attempts == 1:
            raise RuntimeError("device missing")
        return object()

    def _read_loop(self, _endpoint) -> None:
        self.stop_event.set()


def test_reader_reports_reconnect_and_connected(monkeypatch) -> None:
    monkeypatch.setattr("pcpanel.usb_reader.RECONNECT_DELAY_SECONDS", 0)
    stop_event = threading.Event()
    statuses = []
    reader = FlakyReader(stop_event, statuses)

    reader.run()

    assert [status.state for status in statuses] == [
        "starting",
        "reconnecting",
        "connected",
        "stopped",
    ]
    assert statuses[1].message == "device missing"
