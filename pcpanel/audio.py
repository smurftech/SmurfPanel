from __future__ import annotations

import logging
import re
import subprocess
from dataclasses import dataclass
from typing import Protocol

from pcpanel.config import ButtonAction, DialTarget

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class AudioStream:
    id: int
    name: str
    volume: int | None = None
    muted: bool | None = None
    binary: str | None = None
    app_id: str | None = None


@dataclass(frozen=True)
class OutputDevice:
    name: str
    label: str


class AudioBackend(Protocol):
    def list_streams(self) -> list[AudioStream]:
        ...

    def set_volume(self, target: DialTarget, percent: int) -> None:
        ...

    def toggle_mute(self, target: DialTarget) -> None:
        ...

    def list_output_devices(self) -> list[OutputDevice]:
        ...

    def get_default_output_name(self) -> str | None:
        ...

    def set_output_device(self, output_name: str) -> None:
        ...

    def run_button_action(self, action: ButtonAction, target: DialTarget) -> str | None:
        ...


class PactlAudioBackend:
    """Subprocess fallback backend for diagnostics and compatibility."""

    def get_system_volume(self) -> int | None:
        result = self._run(["pactl", "get-sink-volume", "@DEFAULT_SINK@"], capture=True)
        return parse_pactl_volume(result.stdout)

    def get_system_mute(self) -> bool | None:
        result = self._run(["pactl", "get-sink-mute", "@DEFAULT_SINK@"], capture=True)
        return parse_pactl_mute(result.stdout)

    def list_streams(self) -> list[AudioStream]:
        result = self._run(["pactl", "list", "sink-inputs"], capture=True)
        return parse_sink_inputs(result.stdout)

    def list_output_devices(self) -> list[OutputDevice]:
        result = self._run(["pactl", "list", "sinks"], capture=True)
        return parse_sinks(result.stdout)

    def get_default_output_name(self) -> str | None:
        result = self._run(["pactl", "get-default-sink"], capture=True)
        output_name = result.stdout.strip()
        return output_name or None

    def set_volume(self, target: DialTarget, percent: int) -> None:
        percent = max(0, min(100, percent))
        if target.type == "system":
            LOGGER.info("Setting system volume to %s%%", percent)
            self._run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{percent}%"])
            return
        stream_ids = self._resolve_stream_ids(target)
        if stream_ids:
            for stream_id in stream_ids:
                LOGGER.info("Setting stream %s volume to %s%%", stream_id, percent)
                self._run(["pactl", "set-sink-input-volume", str(stream_id), f"{percent}%"])
        else:
            LOGGER.warning("No active stream found for target %s", target.label)

    def set_output_device(self, output_name: str) -> None:
        LOGGER.info("Setting default output device to %s", output_name)
        self._run(["pactl", "set-default-sink", output_name])
        for stream in self.list_streams():
            try:
                self._run(["pactl", "move-sink-input", str(stream.id), output_name])
            except subprocess.CalledProcessError:
                LOGGER.debug("Unable to move stream %s to %s", stream.id, output_name, exc_info=True)

    def run_button_action(self, action: ButtonAction, target: DialTarget) -> str | None:
        if action.type == "mute":
            if target.type == "none":
                LOGGER.info("Button target is unmapped; ignoring mute action")
                return None
            self.toggle_mute(target)
            return f"Toggled mute for {target.label}"
        if action.type == "set_output":
            if not action.output_name:
                LOGGER.warning("Set-output button action has no output device")
                return None
            self.set_output_device(action.output_name)
            return f"Changed output to {action.output_label or action.output_name}"
        if action.type == "toggle_output":
            output_name = self._toggle_output_name(action)
            if output_name is None:
                LOGGER.warning("Toggle-output button action is missing output devices")
                return None
            self.set_output_device(output_name)
            return f"Changed output to {button_action_output_label(action, output_name)}"
        return None

    def toggle_mute(self, target: DialTarget) -> None:
        if target.type == "system":
            LOGGER.info("Toggling system mute")
            self._run(["pactl", "set-sink-mute", "@DEFAULT_SINK@", "toggle"])
            return
        stream_ids = self._resolve_stream_ids(target)
        if stream_ids:
            for stream_id in stream_ids:
                LOGGER.info("Toggling stream %s mute", stream_id)
                self._run(["pactl", "set-sink-input-mute", str(stream_id), "toggle"])
        else:
            LOGGER.warning("No active stream found for target %s", target.label)

    def _resolve_stream_ids(self, target: DialTarget) -> list[int]:
        if target.type != "app":
            return []

        streams = self.list_streams()
        if target.app_id:
            matches = [stream.id for stream in streams if stream.app_id == target.app_id]
            if matches:
                return matches
        if target.binary:
            matches = [stream.id for stream in streams if stream.binary == target.binary]
            if matches:
                return matches
        if target.app_name:
            return [stream.id for stream in streams if stream.name == target.app_name]
        return []

    def _resolve_stream_id(self, target: DialTarget) -> int | None:
        stream_ids = self._resolve_stream_ids(target)
        return stream_ids[0] if stream_ids else None

    def _toggle_output_name(self, action: ButtonAction) -> str | None:
        first = action.output_name
        second = action.toggle_output_name
        if not first:
            return second
        if not second:
            return first
        current = self.get_default_output_name()
        if current == first:
            return second
        return first

    @staticmethod
    def _run(args: list[str], capture: bool = False) -> subprocess.CompletedProcess[str]:
        LOGGER.debug("Running command: %s", " ".join(args))
        result = subprocess.run(
            args,
            check=True,
            capture_output=capture,
            text=True,
            timeout=1,
        )
        LOGGER.debug("Command completed: %s", " ".join(args))
        return result


# Keep the existing public name so the GUI and downstream code do not need a
# broad compatibility migration in R1.1. The implementation is now persistent
# PulseAudio/PipeWire-Pulse rather than cached pactl subprocess calls.
from pcpanel.pulse_audio import PulseAudioBackend as CachedPactlAudioBackend  # noqa: E402


def parse_pactl_volume(stdout: str) -> int | None:
    if match := re.search(r"([0-9]+)%", stdout):
        return int(match.group(1))
    return None


def parse_pactl_mute(stdout: str) -> bool | None:
    if match := re.search(r"Mute:\s*(yes|no)", stdout, re.IGNORECASE):
        return match.group(1).lower() == "yes"
    return None


def parse_sinks(stdout: str) -> list[OutputDevice]:
    devices: list[OutputDevice] = []
    current: dict[str, str | None] | None = None

    for line in stdout.splitlines():
        if re.match(r"\s*Sink #\d+", line):
            if current is not None:
                device = _output_device_from_dict(current)
                if device is not None:
                    devices.append(device)
            current = {"name": None, "description": None}
            continue
        if current is None:
            continue
        if match := re.match(r"\s*Name:\s*(.+)", line):
            current["name"] = match.group(1).strip()
            continue
        if match := re.match(r"\s*Description:\s*(.+)", line):
            current["description"] = match.group(1).strip()

    if current is not None:
        device = _output_device_from_dict(current)
        if device is not None:
            devices.append(device)
    return devices


def parse_sink_inputs(stdout: str) -> list[AudioStream]:
    streams: list[AudioStream] = []
    current: dict[str, object] | None = None

    for line in stdout.splitlines():
        if match := re.match(r"\s*Sink Input #(\d+)", line):
            if current is not None:
                streams.append(_stream_from_dict(current))
            current = {"id": int(match.group(1)), "name": None, "volume": None, "muted": None, "binary": None, "app_id": None}
            continue
        if current is None:
            continue
        if match := re.match(r'\s*application.name\s*=\s*"(.+)"', line):
            current["name"] = match.group(1)
            continue
        if match := re.match(r'\s*application.process.binary\s*=\s*"(.+)"', line):
            current["binary"] = match.group(1)
            continue
        if match := re.match(r'\s*application.id\s*=\s*"(.+)"', line):
            current["app_id"] = match.group(1)
            continue
        if match := re.match(r'\s*media.name\s*=\s*"(.+)"', line):
            current["name"] = current["name"] or match.group(1)
            continue
        if match := re.match(r"\s*Volume:.*?([0-9]+)%", line):
            current["volume"] = int(match.group(1))
            continue
        if match := re.match(r"\s*Mute:\s*(yes|no)", line, re.IGNORECASE):
            current["muted"] = match.group(1).lower() == "yes"

    if current is not None:
        streams.append(_stream_from_dict(current))
    return streams


def button_action_output_label(action: ButtonAction, output_name: str) -> str:
    if output_name == action.output_name:
        return action.output_label or output_name
    if output_name == action.toggle_output_name:
        return action.toggle_output_label or output_name
    return output_name


def _output_device_from_dict(data: dict[str, str | None]) -> OutputDevice | None:
    name = data.get("name")
    if not name:
        return None
    return OutputDevice(name=name, label=data.get("description") or name)


def _stream_from_dict(data: dict[str, object]) -> AudioStream:
    stream_id = int(data["id"])
    name = str(data.get("name") or f"Stream {stream_id}")
    volume = data.get("volume")
    muted = data.get("muted")
    binary = data.get("binary")
    app_id = data.get("app_id")
    return AudioStream(
        id=stream_id,
        name=name,
        volume=volume if isinstance(volume, int) else None,
        muted=muted if isinstance(muted, bool) else None,
        binary=binary if isinstance(binary, str) else None,
        app_id=app_id if isinstance(app_id, str) else None,
    )
