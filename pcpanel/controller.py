from __future__ import annotations

import logging
import queue
import signal
import threading
from pathlib import Path
from collections.abc import Callable

from pcpanel.audio import AudioBackend, PactlAudioBackend
from pcpanel.config import AppConfig, ButtonAction, DialTarget, load_config
from pcpanel.events import ControlEvent, ControlKind
from pcpanel.osd import LoggingOsd, Osd
from pcpanel.usb_reader import PyUsbReader

LOGGER = logging.getLogger(__name__)


class Controller:
    def __init__(
        self,
        config: AppConfig | None = None,
        config_path: Path | None = None,
        audio: AudioBackend | None = None,
        osd: Osd | None = None,
        reader_factory: Callable[[Callable[[ControlEvent], None], threading.Event], threading.Thread] | None = None,
    ) -> None:
        self.config = config or load_config(config_path)
        self.audio = audio or PactlAudioBackend()
        self.osd = osd or LoggingOsd()
        self.stop_event = threading.Event()
        self.events: queue.Queue[ControlEvent] = queue.Queue()
        self.reader_factory = reader_factory or self._default_reader_factory
        self._last_dial_percent: dict[int, int] = {}

    def run_forever(self) -> None:
        signal.signal(signal.SIGTERM, lambda *_: self.stop())
        signal.signal(signal.SIGINT, lambda *_: self.stop())
        reader = self.reader_factory(self.events.put, self.stop_event)
        reader.start()

        LOGGER.info("PCPanel controller started")
        while not self.stop_event.is_set():
            try:
                event = self.events.get(timeout=0.25)
            except queue.Empty:
                continue
            try:
                self.handle_event(event)
            except Exception:
                LOGGER.exception("Failed to handle input event")

    def stop(self) -> None:
        self.stop_event.set()

    def inject_dial(self, control_index: int, value: int) -> None:
        self.handle_event(
            ControlEvent(
                kind=ControlKind.DIAL,
                control_index=control_index,
                value=max(0, min(255, value)),
                raw="manual",
                received_at=0,
            )
        )

    def handle_event(self, event: ControlEvent) -> str | None:
        LOGGER.debug(
            "Received %s %s value=%s raw=%s",
            event.kind.value,
            event.control_number,
            event.value,
            event.raw[:12],
        )
        target = self.config.dials[event.control_index]
        LOGGER.debug(
            "Mapped %s %s to target type=%s label=%s",
            event.kind.value,
            event.control_number,
            target.type,
            target.label,
        )
        if event.kind == ControlKind.DIAL:
            if target.type == "none":
                LOGGER.debug("%s %s is unmapped", event.kind.value, event.control_number)
                return None
            self._handle_dial(target, event)
        elif event.kind == ControlKind.BUTTON and event.is_pressed:
            return self._handle_button(self.config.button_actions[event.control_index], target)
        return None

    def _handle_dial(self, target: DialTarget, event: ControlEvent) -> None:
        previous_percent = self._last_dial_percent.get(event.control_index)
        if previous_percent == event.percent:
            LOGGER.debug("Dial %s percent unchanged at %s%%", event.control_number, event.percent)
            return
        self._last_dial_percent[event.control_index] = event.percent
        self.audio.set_volume(target, event.percent)
        if self.config.osd_enabled:
            self.osd.show_volume(target.label, event.percent)

    def _handle_button(self, action: ButtonAction, target: DialTarget) -> str | None:
        message = self.audio.run_button_action(action, target)
        if self.config.osd_enabled:
            self.osd.show_mute(message or target.label)
        return message

    @staticmethod
    def _default_reader_factory(on_event, stop_event):
        return PyUsbReader(on_event=on_event, stop_event=stop_event)
