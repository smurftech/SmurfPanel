from pcpanel.config import (
    AppConfig,
    DialLighting,
    DialTarget,
    LightingConfig,
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
    assert loaded.lighting.dials[1].enabled is False
    assert loaded.lighting.dials[1].color == "#222222"


def test_missing_config_returns_default(tmp_path) -> None:
    config = load_config(tmp_path / "missing.json")

    assert config.dials[0].type == "system"
    assert config.dials[1].type == "none"
    assert config.lighting.dials[0].color == "#4DA3FF"
