from __future__ import annotations

import json
import logging
import re
import shutil
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Literal, cast


TargetType = Literal["none", "system", "app"]
ButtonActionType = Literal["mute", "set_output", "toggle_output"]
CONFIG_VERSION = 2
DEFAULT_LIGHTING_COLORS = ["#0D6EFD", "#4FC3FF", "#E6F0FF", "#F2F4F7"]
HEX_COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")
LOGGER = logging.getLogger(__name__)


@dataclass
class DialTarget:
    type: TargetType = "none"
    label: str = "None"
    app_name: str | None = None
    app_id: str | None = None
    binary: str | None = None


@dataclass
class DialLighting:
    enabled: bool = True
    color: str = "#0D6EFD"


@dataclass
class ButtonAction:
    type: ButtonActionType = "mute"
    output_name: str | None = None
    output_label: str | None = None
    toggle_output_name: str | None = None
    toggle_output_label: str | None = None


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
    button_actions: list[ButtonAction] = field(
        default_factory=lambda: [ButtonAction() for _ in range(4)]
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

    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        LOGGER.warning("Could not load config %s: %s; using defaults", config_path, exc)
        return AppConfig()
    if not isinstance(data, dict):
        LOGGER.warning("Config %s is not an object; using defaults", config_path)
        return AppConfig()

    dials_data = data.get("dials", [])
    if not isinstance(dials_data, list):
        dials_data = []
    dials = [_dial_from_dict(item) for item in dials_data]
    while len(dials) < 4:
        dials.append(DialTarget())
    button_actions_data = data.get("button_actions", [])
    if not isinstance(button_actions_data, list):
        button_actions_data = []
    button_actions = [_button_action_from_dict(item) for item in button_actions_data]
    while len(button_actions) < 4:
        button_actions.append(ButtonAction())
    lighting_data = data.get("lighting", {})
    if not isinstance(lighting_data, dict):
        lighting_data = {}
    lighting_dials_data = lighting_data.get("dials", [])
    if not isinstance(lighting_dials_data, list):
        lighting_dials_data = []
    lighting_dials = [
        _lighting_from_dict(item, DEFAULT_LIGHTING_COLORS[index])
        for index, item in enumerate(lighting_dials_data[:4])
    ]
    while len(lighting_dials) < 4:
        lighting_dials.append(
            DialLighting(color=DEFAULT_LIGHTING_COLORS[len(lighting_dials)])
        )
    return AppConfig(
        dials=dials[:4],
        button_actions=button_actions[:4],
        osd_enabled=_bool_from_value(data.get("osd_enabled"), True),
        volume_step_hz=_int_from_value(data.get("volume_step_hz"), 60),
        lighting=LightingConfig(
            enabled=_bool_from_value(lighting_data.get("enabled"), True),
            dials=lighting_dials[:4],
        ),
    )


def config_to_json(config: AppConfig) -> str:
    payload = {
        "version": CONFIG_VERSION,
        "dials": [asdict(dial) for dial in config.dials[:4]],
        "button_actions": [asdict(action) for action in config.button_actions[:4]],
        "osd_enabled": config.osd_enabled,
        "volume_step_hz": config.volume_step_hz,
        "lighting": asdict(config.lighting),
    }
    return json.dumps(payload, indent=2)


def save_config(config: AppConfig, path: Path | None = None) -> None:
    config_path = path or default_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)
    if config_path.exists():
        shutil.copy2(config_path, backup_config_path(config_path))
    temp_path = config_path.with_name(f".{config_path.name}.tmp")
    temp_path.write_text(config_to_json(config) + "\n", encoding="utf-8")
    temp_path.replace(config_path)


def backup_config_path(path: Path) -> Path:
    return path.with_name(f"{path.name}.bak")


def _dial_from_dict(data: object) -> DialTarget:
    if not isinstance(data, dict):
        return DialTarget()
    target_type = data.get("type")
    if target_type not in ("none", "system", "app"):
        target_type = "none"
    target_type = cast(TargetType, target_type)
    default_label = "System" if target_type == "system" else "None"
    label = _str_from_value(data.get("label"), default_label)
    if target_type == "app" and label == "None":
        label = _str_from_value(data.get("app_name"), "App")
    return DialTarget(
        type=target_type,
        label=label,
        app_name=_optional_str_from_value(data.get("app_name")),
        app_id=_optional_str_from_value(data.get("app_id")),
        binary=_optional_str_from_value(data.get("binary")),
    )


def _lighting_from_dict(data: object, default_color: str) -> DialLighting:
    if not isinstance(data, dict):
        return DialLighting(color=default_color)
    color = _str_from_value(data.get("color"), default_color).upper()
    if not HEX_COLOR_RE.match(color):
        LOGGER.warning("Invalid LED color %r; using %s", color, default_color)
        color = default_color
    return DialLighting(
        enabled=_bool_from_value(data.get("enabled"), True),
        color=color,
    )


def _button_action_from_dict(data: object) -> ButtonAction:
    if not isinstance(data, dict):
        return ButtonAction()
    action_type = data.get("type")
    if action_type not in ("mute", "set_output", "toggle_output"):
        action_type = "mute"
    action_type = cast(ButtonActionType, action_type)
    return ButtonAction(
        type=action_type,
        output_name=_optional_str_from_value(data.get("output_name")),
        output_label=_optional_str_from_value(data.get("output_label")),
        toggle_output_name=_optional_str_from_value(data.get("toggle_output_name")),
        toggle_output_label=_optional_str_from_value(data.get("toggle_output_label")),
    )


def _bool_from_value(value: object, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in ("true", "1", "yes", "on"):
            return True
        if lowered in ("false", "0", "no", "off"):
            return False
    return default


def _int_from_value(value: object, default: int) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return default
    return default


def _str_from_value(value: object, default: str) -> str:
    if isinstance(value, str) and value.strip():
        return value
    return default


def _optional_str_from_value(value: object) -> str | None:
    if isinstance(value, str) and value.strip():
        return value
    return None
