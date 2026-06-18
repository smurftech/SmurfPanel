from pcpanel.config import AppConfig, DialTarget
from pcpanel.controller import Controller
from pcpanel.events import ControlKind, new_event


class FakeAudio:
    def __init__(self) -> None:
        self.volumes = []
        self.mutes = []

    def list_streams(self):
        return []

    def set_volume(self, target, percent: int) -> None:
        self.volumes.append((target.label, percent))

    def toggle_mute(self, target) -> None:
        self.mutes.append(target.label)


class FakeOsd:
    def __init__(self) -> None:
        self.messages = []

    def show_volume(self, label: str, percent: int) -> None:
        self.messages.append(("volume", label, percent))

    def show_mute(self, label: str) -> None:
        self.messages.append(("mute", label))


def test_controller_routes_dial_to_audio_and_osd() -> None:
    audio = FakeAudio()
    osd = FakeOsd()
    config = AppConfig(dials=[DialTarget(type="system", label="System")] * 4)
    controller = Controller(config=config, audio=audio, osd=osd)

    controller.handle_event(new_event(ControlKind.DIAL, 0, 128, "010080"))

    assert audio.volumes == [("System", 50)]
    assert osd.messages == [("volume", "System", 50)]


def test_controller_ignores_duplicate_dial_percent() -> None:
    audio = FakeAudio()
    controller = Controller(
        config=AppConfig(dials=[DialTarget(type="system", label="System")] * 4),
        audio=audio,
        osd=FakeOsd(),
    )

    controller.handle_event(new_event(ControlKind.DIAL, 0, 128, "010080"))
    controller.handle_event(new_event(ControlKind.DIAL, 0, 128, "010080"))

    assert audio.volumes == [("System", 50)]


def test_controller_toggles_mute_on_button_press_only() -> None:
    audio = FakeAudio()
    controller = Controller(
        config=AppConfig(dials=[DialTarget(type="system", label="System")] * 4),
        audio=audio,
        osd=FakeOsd(),
    )

    controller.handle_event(new_event(ControlKind.BUTTON, 0, 0, "020000"))
    controller.handle_event(new_event(ControlKind.BUTTON, 0, 1, "020001"))

    assert audio.mutes == ["System"]
