from __future__ import annotations

import logging
import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pulsectl

from pcpanel.config import ButtonAction, DialTarget

LOGGER = logging.getLogger(__name__)


class PulseAudioBackend:
    """Persistent PulseAudio/PipeWire-Pulse backend.

    The connection is created lazily so importing or constructing the backend
    remains safe in tests and packaging checks that do not have an audio server.
    """

    def __init__(self, client_name: str = "pcpanel") -> None:
        self.client_name = client_name
        self._pulse: pulsectl.Pulse | None = None
        self._lock = threading.RLock()
        self._cached_streams = []
        self._cached_outputs = []
        self._cached_default_output_name: str | None = None

    def close(self) -> None:
        with self._lock:
            if self._pulse is not None:
                self._pulse.close()
                self._pulse = None

    def list_streams(self):
        from pcpanel.audio import AudioStream

        with self._lock:
            streams = [self._stream_from_info(info) for info in self._client().sink_input_list()]
            self._cached_streams = streams
            return list(streams)

    def list_output_devices(self):
        from pcpanel.audio import OutputDevice

        with self._lock:
            outputs = [
                OutputDevice(name=sink.name, label=sink.description or sink.name)
                for sink in self._client().sink_list()
            ]
            self._cached_outputs = outputs
            return list(outputs)

    def get_default_output_name(self) -> str | None:
        with self._lock:
            self._cached_default_output_name = self._client().server_info().default_sink_name
            return self._cached_default_output_name

    def get_system_volume(self) -> int | None:
        with self._lock:
            sink = self._default_sink()
            if sink is None:
                return None
            return round(float(sink.volume.value_flat) * 100)

    def get_system_mute(self) -> bool | None:
        with self._lock:
            sink = self._default_sink()
            return bool(sink.mute) if sink is not None else None

    def set_volume(self, target: DialTarget, percent: int) -> None:
        level = max(0, min(100, percent)) / 100.0
        with self._lock:
            pulse = self._client()
            if target.type == "system":
                sink = self._default_sink()
                if sink is None:
                    return
                pulse.volume_set_all_chans(sink, level)
                return

            streams = self._matching_sink_inputs(target)
            if not streams:
                LOGGER.warning("No active stream found for target %s", target.label)
                return
            for stream in streams:
                pulse.volume_set_all_chans(stream, level)

    def toggle_mute(self, target: DialTarget) -> None:
        with self._lock:
            pulse = self._client()
            if target.type == "system":
                sink = self._default_sink()
                if sink is None:
                    return
                pulse.mute(sink, not bool(sink.mute))
                return

            streams = self._matching_sink_inputs(target)
            if not streams:
                LOGGER.warning("No active stream found for target %s", target.label)
                return
            mute = not all(bool(stream.mute) for stream in streams)
            for stream in streams:
                pulse.mute(stream, mute)

    def set_output_device(self, output_name: str) -> None:
        with self._lock:
            pulse = self._client()
            sink = next((item for item in pulse.sink_list() if item.name == output_name), None)
            if sink is None:
                raise RuntimeError(f"Output device not found: {output_name}")
            pulse.default_set(sink)
            for stream in pulse.sink_input_list():
                pulse.sink_input_move(stream.index, sink.index)
            self._cached_default_output_name = output_name

    def run_button_action(self, action: ButtonAction, target: DialTarget) -> str | None:
        if action.type == "mute":
            if target.type == "none":
                return None
            self.toggle_mute(target)
            return f"Toggled mute for {target.label}"
        if action.type == "set_output":
            if not action.output_name:
                return None
            self.set_output_device(action.output_name)
            return f"Changed output to {action.output_label or action.output_name}"
        if action.type == "toggle_output":
            output_name = self._toggle_output_name(action)
            if output_name is None:
                return None
            self.set_output_device(output_name)
            return f"Changed output to {self._output_label(action, output_name)}"
        return None

    # Compatibility hooks retained for the existing GUI refresh path and tests.
    def set_cached_streams(self, streams) -> None:
        self._cached_streams = list(streams)

    def set_cached_output_devices(self, outputs) -> None:
        self._cached_outputs = list(outputs)

    def set_cached_default_output_name(self, output_name: str | None) -> None:
        self._cached_default_output_name = output_name

    def _resolve_stream_id(self, target: DialTarget) -> int | None:
        if target.type != "app":
            return None
        if target.app_id:
            for stream in self._cached_streams:
                if stream.app_id == target.app_id:
                    return stream.id
        for stream in self._cached_streams:
            if target.binary and stream.binary == target.binary:
                return stream.id
            if target.app_name and stream.name == target.app_name:
                return stream.id
        return None

    def _matching_sink_inputs(self, target: DialTarget):
        if target.type != "app":
            return []
        streams = self._client().sink_input_list()

        if target.app_id:
            matches = [
                stream
                for stream in streams
                if stream.proplist.get("application.id") == target.app_id
            ]
            if matches:
                return matches

        if target.binary:
            matches = [
                stream
                for stream in streams
                if stream.proplist.get("application.process.binary") == target.binary
            ]
            if matches:
                return matches
        if target.app_name:
            return [
                stream
                for stream in streams
                if (
                    stream.proplist.get("application.name") == target.app_name
                    or stream.name == target.app_name
                )
            ]
        return []

    def _toggle_output_name(self, action: ButtonAction) -> str | None:
        first = action.output_name
        second = action.toggle_output_name
        if not first:
            return second
        if not second:
            return first
        current = self._cached_default_output_name
        if current is None:
            current = self.get_default_output_name()
        return second if current == first else first

    def _default_sink(self):
        pulse = self._client()
        default_name = pulse.server_info().default_sink_name
        return next((sink for sink in pulse.sink_list() if sink.name == default_name), None)

    def _client(self) -> pulsectl.Pulse:
        if self._pulse is None:
            import pulsectl

            self._pulse = pulsectl.Pulse(self.client_name)
        return self._pulse

    @staticmethod
    def _stream_from_info(info):
        from pcpanel.audio import AudioStream

        name = info.proplist.get("application.name") or info.name or f"Stream {info.index}"
        return AudioStream(
            id=int(info.index),
            name=str(name),
            volume=round(float(info.volume.value_flat) * 100),
            muted=bool(info.mute),
            binary=info.proplist.get("application.process.binary"),
            app_id=info.proplist.get("application.id"),
        )

    @staticmethod
    def _output_label(action: ButtonAction, output_name: str) -> str:
        if output_name == action.output_name:
            return action.output_label or output_name
        if output_name == action.toggle_output_name:
            return action.toggle_output_label or output_name
        return output_name
