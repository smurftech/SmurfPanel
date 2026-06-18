from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Literal


TargetType = Literal["none", "system", "app"]
DEFAULT_LIGHTING_COLORS = ["#4DA3FF", "#35D0BA", "#A78BFA", "#F7C948"]


@dataclass
class DialTarget:
    type: TargetType = "none"
    label: str = "None"
    app_name: str | None = None
    binary: str | None = None
    stream_id: int | None = None


@dataclass
class DialLighting:
    enabled: bool = True
    color: str = "#4DA3FF"


@dataclass
class LightingConfig:
    enabled: bool = True
    dials: list[DialLighting] = field(
        default_factory=lambda: [
            DialLighting(color=color) for color in DEFAULT_LIGHTING_COLORS
        ]
    )


@dataclass
class AppConfig:
    dials: list[DialTarget] = field(
        default_factory=lambda: [
            DialTarget(type="system", label="System"),
            DialTarget(),
            DialTarget(),
            DialTarget(),
        ]
    )
    osd_enabled: bool = True
    volume_step_hz: int = 60
    lighting: LightingConfig = field(default_factory=LightingConfig)


def default_config_path() -> Path:
    return Path.home() / ".config" / "pcpanel" / "config.json"


def load_config(path: Path | None = None) -> AppConfig:
    config_path = path or default_config_path()
    if not config_path.exists():
        return AppConfig()

    data = json.loads(config_path.read_text(encoding="utf-8"))
    dials = [DialTarget(**item) for item in data.get("dials", [])]
    while len(dials) < 4:
        dials.append(DialTarget())
    lighting_data = data.get("lighting", {})
    lighting_dials = [
        DialLighting(**item) for item in lighting_data.get("dials", [])
    ]
    while len(lighting_dials) < 4:
        lighting_dials.append(
            DialLighting(color=DEFAULT_LIGHTING_COLORS[len(lighting_dials)])
        )
    return AppConfig(
        dials=dials[:4],
        osd_enabled=bool(data.get("osd_enabled", True)),
        volume_step_hz=int(data.get("volume_step_hz", 60)),
        lighting=LightingConfig(
            enabled=bool(lighting_data.get("enabled", True)),
            dials=lighting_dials[:4],
        ),
    )


def config_to_json(config: AppConfig) -> str:
    payload = {
        "dials": [asdict(dial) for dial in config.dials[:4]],
        "osd_enabled": config.osd_enabled,
        "volume_step_hz": config.volume_step_hz,
        "lighting": asdict(config.lighting),
    }
    return json.dumps(payload, indent=2)


def save_config(config: AppConfig, path: Path | None = None) -> None:
    config_path = path or default_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(config_to_json(config) + "\n", encoding="utf-8")
