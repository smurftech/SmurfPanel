from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum

from pcpanel.events import ControlEvent
from pcpanel.usb_reader import PyUsbReader

LOGGER = logging.getLogger(__name__)


class DeviceState(str, Enum):
    STOPPED = "stopped"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    RECONNECTING = "reconnecting"


@dataclass(frozen=True)
class DeviceStatus:
    state: DeviceState
    message: str = ""
    attempt: int = 0


ReaderFactory = Callable[..., PyUsbReader]
StateCallback = Callable[[DeviceStatus], None]


class DeviceService(threading.Thread):
    """Own the long-lived lifecycle of the PCPanel USB connection.

    PyUsbReader represents one connection attempt. DeviceService keeps retrying
    after a failed open or a lost connection until the shared stop event is set.
    """

    def __init__(
        self,
        on_event: Callable[[ControlEvent], None],
        stop_event: threading.Event,
        on_state: StateCallback | None = None,
        reader_factory: ReaderFactory = PyUsbReader,
        reconnect_delay: float = 1.0,
        max_reconnect_delay: float = 8.0,
    ) -> None:
        super().__init__(daemon=True)
        self.on_event = on_event
        self.stop_event = stop_event
        self.on_state = on_state or (lambda _status: None)
        self.reader_factory = reader_factory
        self.reconnect_delay = max(0.05, reconnect_delay)
        self.max_reconnect_delay = max(self.reconnect_delay, max_reconnect_delay)
        self._reader_lock = threading.Lock()
        self._reader: PyUsbReader | None = None
        self._connected = False
        self._attempt = 0

    @property
    def connected(self) -> bool:
        with self._reader_lock:
            return self._connected

    def run(self) -> None:
        first_attempt = True
        while not self.stop_event.is_set():
            state = DeviceState.CONNECTING if first_attempt else DeviceState.RECONNECTING
            self._emit(state, attempt=self._attempt)
            first_attempt = False

            disconnected_message = "USB connection ended"
            reader = self.reader_factory(
                on_event=self.on_event,
                stop_event=self.stop_event,
                on_connected=self._on_connected,
                on_disconnected=lambda message: self._on_disconnected(message),
            )
            with self._reader_lock:
                self._reader = reader
                self._connected = False

            reader.start()
            reader.join()

            with self._reader_lock:
                self._reader = None
                was_connected = self._connected
                self._connected = False

            if self.stop_event.is_set():
                break

            if reader.last_error:
                disconnected_message = reader.last_error
            elif was_connected:
                disconnected_message = "USB connection lost"

            self._attempt += 1
            self._emit(
                DeviceState.DISCONNECTED,
                disconnected_message,
                attempt=self._attempt,
            )

            delay = min(
                self.reconnect_delay * (2 ** min(self._attempt - 1, 3)),
                self.max_reconnect_delay,
            )
            if self.stop_event.wait(delay):
                break

        self._emit(DeviceState.STOPPED, attempt=self._attempt)

    def send_output_report(self, payload: bytes) -> None:
        with self._reader_lock:
            reader = self._reader
            connected = self._connected
        if reader is None or not connected:
            raise RuntimeError("PCPanel USB device is not connected")
        reader.send_output_report(payload)

    def _on_connected(self) -> None:
        with self._reader_lock:
            self._connected = True
        self._attempt = 0
        self._emit(DeviceState.CONNECTED)

    def _on_disconnected(self, message: str | None) -> None:
        with self._reader_lock:
            self._connected = False
        if message:
            LOGGER.info("PCPanel USB connection ended: %s", message)

    def _emit(
        self,
        state: DeviceState,
        message: str = "",
        attempt: int | None = None,
    ) -> None:
        status = DeviceStatus(
            state=state,
            message=message,
            attempt=self._attempt if attempt is None else attempt,
        )
        LOGGER.info("Device state: %s%s", state.value, f" ({message})" if message else "")
        try:
            self.on_state(status)
        except Exception:
            LOGGER.exception("Device state callback failed")
