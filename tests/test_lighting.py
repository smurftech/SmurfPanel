from pcpanel.config import DialLighting
from pcpanel.lighting import build_mini_dial_colors, colors_for_device


def test_build_mini_dial_colors_static_slots() -> None:
    payload = build_mini_dial_colors(["#FF0000", "#00FF00", "#0000FF", "#FFFFFF"])

    assert len(payload) == 64
    assert payload[:30] == bytes.fromhex(
        "0602"
        "01ff0000000000"
        "0100ff00000000"
        "010000ff000000"
        "01ffffff000000"
    )


def test_colors_for_device_uses_black_when_disabled() -> None:
    colors = colors_for_device(
        [
            DialLighting(enabled=True, color="#111111"),
            DialLighting(enabled=False, color="#222222"),
        ]
    )

    assert colors == ["#111111", "#000000"]
