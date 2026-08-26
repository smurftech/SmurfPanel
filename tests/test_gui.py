from pcpanel.audio import AudioStream
from pcpanel.config import ButtonAction, DialTarget
from pcpanel.gui.app import (
    app_version,
    build_target_options,
    button_action_label,
    reader_status_text,
    target_matches_stream,
    toggled_app_mute_streams,
)
from pcpanel.gui.widgets import _display_path
from pcpanel.usb_reader import ReaderStatus


def test_reader_status_text_formats_reconnect_message() -> None:
    label, message = reader_status_text(
        ReaderStatus(state="reconnecting", message="device missing")
    )

    assert label == "Device: reconnecting"
    assert message == "USB reconnecting: device missing"


def test_button_action_label_formats_toggle_outputs() -> None:
    label = button_action_label(
        ButtonAction(
            type="toggle_output",
            output_name="sink.headphones",
            output_label="Headphones",
            toggle_output_name="sink.speakers",
            toggle_output_label="Speakers",
        )
    )

    assert label == "toggle Headphones / Speakers"


def test_app_version_returns_package_version() -> None:
    assert app_version() == "0.1.0"


def test_display_path_shortens_home_path() -> None:
    assert _display_path("~/.config/pcpanel/config.json") == "~/.config/pcpanel/config.json"


def test_saved_inactive_app_remains_in_target_options() -> None:
    saved = DialTarget(
        type="app",
        label="Firefox",
        app_name="Firefox",
        app_id="org.mozilla.firefox",
        binary="firefox",
    )

    options = build_target_options([saved], [])

    assert ("Firefox (saved, inactive)", saved) in options


def test_target_options_deduplicate_multiple_streams_for_same_identity() -> None:
    streams = [
        AudioStream(41, "Firefox", binary="firefox", app_id="org.mozilla.firefox"),
        AudioStream(42, "Firefox", binary="firefox", app_id="org.mozilla.firefox"),
    ]

    options = build_target_options([], streams)

    assert len(options) == 3
    assert options[2][0] == "Firefox (firefox)"


def test_target_matching_prefers_app_id_but_falls_back_to_binary() -> None:
    identified = DialTarget(type="app", label="Firefox", app_id="org.mozilla.firefox", binary="firefox")
    legacy = DialTarget(type="app", label="Firefox", binary="firefox")
    stream = AudioStream(42, "Browser", binary="firefox", app_id="org.mozilla.firefox")

    assert target_matches_stream(identified, stream) is True
    assert target_matches_stream(legacy, stream) is True
    assert target_matches_stream(
        identified,
        AudioStream(43, "Browser", binary="firefox", app_id="com.google.Chrome"),
    ) is False


def test_cached_app_mute_updates_all_matching_streams_immediately() -> None:
    target = DialTarget(type="app", label="Firefox", app_id="org.mozilla.firefox")
    streams = [
        AudioStream(41, "Firefox", muted=False, app_id="org.mozilla.firefox"),
        AudioStream(42, "Firefox", muted=False, app_id="org.mozilla.firefox"),
        AudioStream(99, "Spotify", muted=False, app_id="com.spotify.Client"),
    ]

    muted = toggled_app_mute_streams(streams, target)
    unmuted = toggled_app_mute_streams(muted, target)

    assert [stream.muted for stream in muted] == [True, True, False]
    assert [stream.muted for stream in unmuted] == [False, False, False]
