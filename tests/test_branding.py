from pathlib import Path

from pcpanel.autostart import APP_NAME
from pcpanel.config import DEFAULT_LIGHTING_COLORS
from pcpanel.gui.brand_tokens import (
    BRAND_DEVKIT_REVISION,
    BRAND_DEVKIT_SOURCE,
    SMURFTECH_BORDERS,
    SMURFTECH_COLORS,
    SMURFTECH_RADII,
)
from pcpanel.gui.resources import BRAND_FONT_FILES, resource_path
from pcpanel.gui.style import APP_STYLE


ROOT = Path(__file__).resolve().parents[1]


def test_smurftech_base_palette_is_applied() -> None:
    for color in SMURFTECH_COLORS.values():
        assert color in APP_STYLE or color in DEFAULT_LIGHTING_COLORS

    assert DEFAULT_LIGHTING_COLORS == [
        SMURFTECH_COLORS["electric_blue"],
        SMURFTECH_COLORS["cyan_accent"],
        SMURFTECH_COLORS["ice_blue"],
        SMURFTECH_COLORS["clean_white"],
    ]


def test_smurftech_token_snapshot_matches_v1_contract() -> None:
    assert BRAND_DEVKIT_SOURCE == "brands/smurftech/tokens/smurftech.tokens.json"
    assert len(BRAND_DEVKIT_REVISION) == 40
    assert SMURFTECH_COLORS == {
        "deep_night": "#0C111A",
        "night_slate": "#121826",
        "steel_blue": "#1E2A3A",
        "electric_blue": "#0D6EFD",
        "cyan_accent": "#4FC3FF",
        "ice_blue": "#E6F0FF",
        "clean_white": "#F2F4F7",
    }
    assert SMURFTECH_RADII == {
        "small": "6px",
        "medium": "8px",
        "large": "12px",
    }
    assert SMURFTECH_BORDERS == {
        "default": SMURFTECH_COLORS["steel_blue"],
        "active": SMURFTECH_COLORS["electric_blue"],
    }


def test_brand_typography_is_bundled_with_approved_fallback_stacks() -> None:
    assert "font-family: Inter" in APP_STYLE
    assert "font-family: Orbitron, Rajdhani, Inter" in APP_STYLE
    assert "font-family: Rajdhani, Inter" in APP_STYLE
    assert len(BRAND_FONT_FILES) == 4
    assert all(resource_path(font_file).is_file() for font_file in BRAND_FONT_FILES)


def test_user_facing_desktop_name_is_smurfpanel() -> None:
    launcher = (ROOT / "packaging" / "pcpanel-gui.desktop").read_text(encoding="utf-8")
    project = (ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert APP_NAME == "SmurfPanel"
    assert "Name=SmurfPanel" in launcher
    assert 'smurfpanel = "pcpanel.__main__:main"' in project
    assert 'smurfpanel-gui = "pcpanel.gui.app:main"' in project
