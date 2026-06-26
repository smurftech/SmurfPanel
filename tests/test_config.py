from pcpanel.config import (
    AppConfig,
    ButtonAction,
    CONFIG_VERSION,
    DialLighting,
    DialTarget,
    LightingConfig,
    backup_config_path,
    config_to_json,
    load_config,
    save_config,
)


def test_save_and_load_config(tmp_path) -> None:
    path = tmp_path / "config.json"
    config = AppConfig(
        dials=[
            DialTarget(type="system", label="System"),
            DialTarget(type="app", label="Firefox", app_name="Firefox", binary="firefox"),
            DialTarget(type="none", label="None"),
            DialTarget(type="system", label="Headphones"),
        ],
        button_actions=[
            ButtonAction(type="mute"),
            ButtonAction(type="set_output", output_name="sink.headphones", output_label="Headphones"),
            ButtonAction(
                type="toggle_output",
                output_name="sink.headphones",
                output_label="Headphones",
                toggle_output_name="sink.speakers",
                toggle_output_label="Speakers",
            ),
            ButtonAction(type="mute"),
        ],
        osd_enabled=False,
        volume_step_hz=30,
        lighting=LightingConfig(
            dials=[
                DialLighting(enabled=True, color="#111111"),
                DialLighting(enabled=False, color="#222222"),
                DialLighting(enabled=True, color="#333333"),
                DialLighting(enabled=True, color="#444444"),
            ]
        ),
    )

    save_config(config, path)
    loaded = load_config(path)

    assert loaded.osd_enabled is False
    assert loaded.volume_step_hz == 30
    assert loaded.dials[1].type == "app"
    assert loaded.dials[1].label == "Firefox"
    assert loaded.dials[1].binary == "firefox"
    assert loaded.button_actions[1].type == "set_output"
    assert loaded.button_actions[1].output_name == "sink.headphones"
    assert loaded.button_actions[2].type == "toggle_output"
    assert loaded.button_actions[2].toggle_output_name == "sink.speakers"
    assert loaded.lighting.dials[1].enabled is False
    assert loaded.lighting.dials[1].color == "#222222"
    assert backup_config_path(path).exists() is False


def test_missing_config_returns_default(tmp_path) -> None:
    config = load_config(tmp_path / "missing.json")

    assert config.dials[0].type == "system"
    assert config.dials[1].type == "none"
    assert config.button_actions[0].type == "mute"
    assert config.lighting.dials[0].color == "#4DA3FF"


def test_config_json_includes_version() -> None:
    payload = config_to_json(AppConfig())

    assert f'"version": {CONFIG_VERSION}' in payload


def test_save_config_backs_up_existing_file(tmp_path) -> None:
    path = tmp_path / "config.json"
    path.write_text('{"old": true}\n', encoding="utf-8")

    save_config(AppConfig(), path)

    assert backup_config_path(path).read_text(encoding="utf-8") == '{"old": true}\n'
    assert f'"version": {CONFIG_VERSION}' in path.read_text(encoding="utf-8")


def test_load_config_ignores_unknown_and_invalid_values(tmp_path) -> None:
    path = tmp_path / "config.json"
    path.write_text(
        """
{
  "version": 99,
  "dials": [
    {"type": "app", "label": "Firefox", "binary": "firefox", "stream_id": "42", "extra": "ignored"},
    {"type": "bogus", "label": ""}
  ],
  "button_actions": [
    {"type": "set_output", "output_name": "sink.headphones", "output_label": "Headphones", "extra": "ignored"},
    {"type": "bogus", "output_name": "sink.speakers"}
  ],
  "osd_enabled": "false",
  "volume_step_hz": "30",
  "lighting": {
    "enabled": "yes",
    "dials": [
      {"enabled": "off", "color": "not-a-color"}
    ]
  }
}
""",
        encoding="utf-8",
    )

    config = load_config(path)

    assert config.dials[0].type == "app"
    assert config.dials[0].stream_id == 42
    assert config.dials[1].type == "none"
    assert config.button_actions[0].type == "set_output"
    assert config.button_actions[0].output_name == "sink.headphones"
    assert config.button_actions[1].type == "mute"
    assert config.osd_enabled is False
    assert config.volume_step_hz == 30
    assert config.lighting.enabled is True
    assert config.lighting.dials[0].enabled is False
    assert config.lighting.dials[0].color == "#4DA3FF"


def test_load_config_uses_defaults_for_malformed_json(tmp_path) -> None:
    path = tmp_path / "config.json"
    path.write_text("{ nope", encoding="utf-8")

    config = load_config(path)

    assert config.dials[0].type == "system"
