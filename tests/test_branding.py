from pathlib import Path

from pcpanel.autostart import APP_NAME
from pcpanel.config import DEFAULT_LIGHTING_COLORS
from pcpanel.gui.style import APP_STYLE


ROOT = Path(__file__).resolve().parents[1]


def test_smurftech_base_palette_is_applied() -> None:
    for color in (
        "#0C111A",
        "#121826",
        "#1E2A3A",
        "#0D6EFD",
        "#4FC3FF",
        "#E6F0FF",
        "#F2F4F7",
    ):
        assert color in APP_STYLE or color in DEFAULT_LIGHTING_COLORS

    assert DEFAULT_LIGHTING_COLORS == [
        "#0D6EFD",
        "#4FC3FF",
        "#E6F0FF",
        "#F2F4F7",
    ]


def test_brand_typography_uses_approved_fallback_stacks() -> None:
    assert "font-family: Inter" in APP_STYLE
    assert "font-family: Orbitron, Rajdhani, Inter" in APP_STYLE
    assert "font-family: Rajdhani, Inter" in APP_STYLE


def test_user_facing_desktop_name_is_smurfpanel() -> None:
    launcher = (ROOT / "packaging" / "pcpanel-gui.desktop").read_text(encoding="utf-8")
    project = (ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert APP_NAME == "SmurfPanel"
    assert "Name=SmurfPanel" in launcher
    assert 'smurfpanel = "pcpanel.__main__:main"' in project
    assert 'smurfpanel-gui = "pcpanel.gui.app:main"' in project
