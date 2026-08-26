import errno
import threading

import usb.core

from pcpanel.usb_reader import (
    PyUsbReader,
    _is_timeout_error,
    reconnect_delay_for_attempt,
    usb_permission_error_message,
)


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


def test_reconnect_backoff_is_bounded(monkeypatch) -> None:
    monkeypatch.setattr("pcpanel.usb_reader.RECONNECT_DELAY_SECONDS", 1.0)
    monkeypatch.setattr("pcpanel.usb_reader.MAX_RECONNECT_DELAY_SECONDS", 8.0)

    assert reconnect_delay_for_attempt(0) == 1.0
    assert reconnect_delay_for_attempt(1) == 1.0
    assert reconnect_delay_for_attempt(2) == 2.0
    assert reconnect_delay_for_attempt(3) == 4.0
    assert reconnect_delay_for_attempt(4) == 8.0
    assert reconnect_delay_for_attempt(10) == 8.0


def test_timeout_detection_does_not_treat_unknown_usb_errors_as_timeouts() -> None:
    timeout = usb.core.USBError("timed out", errno=errno.ETIMEDOUT)
    unknown = usb.core.USBError("device vanished")

    assert _is_timeout_error(timeout) is True
    assert _is_timeout_error(unknown) is False


def test_usb_permission_error_is_actionable() -> None:
    message = usb_permission_error_message()

    assert "0483:a3c4" in message
    assert "scripts/install_udev_rules.sh" in message
    assert "unplug" in message.lower()
