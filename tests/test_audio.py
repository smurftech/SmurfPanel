from pcpanel.audio import parse_pactl_mute, parse_pactl_volume, parse_sink_inputs


def test_parse_pactl_system_volume() -> None:
    assert parse_pactl_volume("Volume: front-left: 22938 / 35% / -27.35 dB") == 35


def test_parse_pactl_system_mute() -> None:
    assert parse_pactl_mute("Mute: yes") is True
    assert parse_pactl_mute("Mute: no") is False


def test_parse_sink_inputs_extracts_stable_metadata() -> None:
    streams = parse_sink_inputs(
        """
Sink Input #42
    Properties:
        application.name = "Firefox"
        application.process.binary = "firefox"
        media.name = "AudioStream"
    Volume: front-left: 32768 / 50% / -18.06 dB, front-right: 32768 / 50% / -18.06 dB
    Mute: no
"""
    )

    assert len(streams) == 1
    assert streams[0].id == 42
    assert streams[0].name == "Firefox"
    assert streams[0].binary == "firefox"
    assert streams[0].volume == 50
    assert streams[0].muted is False
