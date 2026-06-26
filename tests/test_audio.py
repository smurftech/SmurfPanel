from pcpanel.audio import (
    AudioStream,
    CachedPactlAudioBackend,
    OutputDevice,
    parse_sinks,
    parse_pactl_mute,
    parse_pactl_volume,
    parse_sink_inputs,
)
from pcpanel.config import ButtonAction, DialTarget


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


def test_parse_sinks_extracts_output_devices() -> None:
    devices = parse_sinks(
        """
Sink #1
    State: RUNNING
    Name: alsa_output.pci-speakers
    Description: Speakers
Sink #2
    State: IDLE
    Name: bluez_output.headphones
    Description: Headphones
"""
    )

    assert devices == [
        OutputDevice(name="alsa_output.pci-speakers", label="Speakers"),
        OutputDevice(name="bluez_output.headphones", label="Headphones"),
    ]


def test_cached_backend_resolves_app_stream_without_refreshing(monkeypatch) -> None:
    backend = CachedPactlAudioBackend()
    backend.set_cached_streams([AudioStream(id=42, name="Firefox", binary="firefox")])

    def fail_if_called():
        raise AssertionError("cached app lookup should not refresh streams")

    monkeypatch.setattr(backend, "list_streams", fail_if_called)

    stream_id = backend._resolve_stream_id(
        DialTarget(type="app", label="Firefox", app_name="Firefox", binary="firefox")
    )

    assert stream_id == 42


class RecordingCachedBackend(CachedPactlAudioBackend):
    def __init__(self) -> None:
        super().__init__()
        self.outputs = []

    def set_output_device(self, output_name: str) -> None:
        self.outputs.append(output_name)
        self.set_cached_default_output_name(output_name)


def test_button_action_sets_output_device() -> None:
    backend = RecordingCachedBackend()

    message = backend.run_button_action(
        ButtonAction(
            type="set_output",
            output_name="bluez_output.headphones",
            output_label="Headphones",
        ),
        DialTarget(type="none", label="None"),
    )

    assert backend.outputs == ["bluez_output.headphones"]
    assert message == "Changed output to Headphones"


def test_button_action_toggles_between_outputs() -> None:
    backend = RecordingCachedBackend()
    backend.set_cached_default_output_name("alsa_output.speakers")
    action = ButtonAction(
        type="toggle_output",
        output_name="alsa_output.speakers",
        output_label="Speakers",
        toggle_output_name="bluez_output.headphones",
        toggle_output_label="Headphones",
    )

    first_message = backend.run_button_action(action, DialTarget(type="none", label="None"))
    second_message = backend.run_button_action(action, DialTarget(type="none", label="None"))

    assert backend.outputs == ["bluez_output.headphones", "alsa_output.speakers"]
    assert first_message == "Changed output to Headphones"
    assert second_message == "Changed output to Speakers"
