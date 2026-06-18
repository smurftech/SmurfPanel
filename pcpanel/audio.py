from __future__ import annotations

import re
import subprocess
import logging
from dataclasses import dataclass
from typing import Protocol

from pcpanel.config import DialTarget

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class AudioStream:
    id: int
    name: str
    volume: int | None = None
    muted: bool | None = None
    binary: str | None = None


class AudioBackend(Protocol):
    def list_streams(self) -> list[AudioStream]:
        ...

    def set_volume(self, target: DialTarget, percent: int) -> None:
        ...

    def toggle_mute(self, target: DialTarget) -> None:
        ...


class PactlAudioBackend:
    """Small fallback backend. Prefer a pulsectl backend for production."""

    def get_system_volume(self) -> int | None:
        result = self._run(["pactl", "get-sink-volume", "@DEFAULT_SINK@"], capture=True)
        return parse_pactl_volume(result.stdout)

    def get_system_mute(self) -> bool | None:
        result = self._run(["pactl", "get-sink-mute", "@DEFAULT_SINK@"], capture=True)
        return parse_pactl_mute(result.stdout)

    def list_streams(self) -> list[AudioStream]:
        result = self._run(["pactl", "list", "sink-inputs"], capture=True)
        return parse_sink_inputs(result.stdout)

    def set_volume(self, target: DialTarget, percent: int) -> None:
        percent = max(0, min(100, percent))
        if target.type == "system":
            LOGGER.info("Setting system volume to %s%%", percent)
            self._run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{percent}%"])
            return
        stream_id = self._resolve_stream_id(target)
        if stream_id is not None:
            LOGGER.info("Setting stream %s volume to %s%%", stream_id, percent)
            self._run(["pactl", "set-sink-input-volume", str(stream_id), f"{percent}%"])
        else:
            LOGGER.warning("No active stream found for target %s", target.label)

    def toggle_mute(self, target: DialTarget) -> None:
        if target.type == "system":
            LOGGER.info("Toggling system mute")
            self._run(["pactl", "set-sink-mute", "@DEFAULT_SINK@", "toggle"])
            return
        stream_id = self._resolve_stream_id(target)
        if stream_id is not None:
            LOGGER.info("Toggling stream %s mute", stream_id)
            self._run(["pactl", "set-sink-input-mute", str(stream_id), "toggle"])
        else:
            LOGGER.warning("No active stream found for target %s", target.label)

    def _resolve_stream_id(self, target: DialTarget) -> int | None:
        if target.type != "app":
            return None
        if target.stream_id is not None:
            return target.stream_id

        for stream in self.list_streams():
            if target.binary and stream.binary == target.binary:
                return stream.id
            if target.app_name and stream.name == target.app_name:
                return stream.id
        return None

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


def parse_pactl_volume(stdout: str) -> int | None:
    if match := re.search(r"([0-9]+)%", stdout):
        return int(match.group(1))
    return None


def parse_pactl_mute(stdout: str) -> bool | None:
    if match := re.search(r"Mute:\s*(yes|no)", stdout, re.IGNORECASE):
        return match.group(1).lower() == "yes"
    return None


def parse_sink_inputs(stdout: str) -> list[AudioStream]:
    streams: list[AudioStream] = []
    current: dict[str, object] | None = None

    for line in stdout.splitlines():
        if match := re.match(r"\s*Sink Input #(\d+)", line):
            if current is not None:
                streams.append(_stream_from_dict(current))
            current = {"id": int(match.group(1)), "name": None, "volume": None, "muted": None, "binary": None}
            continue
        if current is None:
            continue
        if match := re.match(r'\s*application.name\s*=\s*"(.+)"', line):
            current["name"] = match.group(1)
            continue
        if match := re.match(r'\s*application.process.binary\s*=\s*"(.+)"', line):
            current["binary"] = match.group(1)
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


def _stream_from_dict(data: dict[str, object]) -> AudioStream:
    stream_id = int(data["id"])
    name = str(data.get("name") or f"Stream {stream_id}")
    volume = data.get("volume")
    muted = data.get("muted")
    binary = data.get("binary")
    return AudioStream(
        id=stream_id,
        name=name,
        volume=volume if isinstance(volume, int) else None,
        muted=muted if isinstance(muted, bool) else None,
        binary=binary if isinstance(binary, str) else None,
    )
