from pcpanel.events import ControlKind
from pcpanel.parser import ReportParseError, parse_report


def test_parse_button_press_from_capture() -> None:
    event = parse_report(bytes.fromhex("020001" + "00" * 61))

    assert event.kind == ControlKind.BUTTON
    assert event.control_index == 0
    assert event.control_number == 1
    assert event.value == 1
    assert event.is_pressed


def test_parse_button_release_from_capture() -> None:
    event = parse_report(bytes.fromhex("020000" + "00" * 61))

    assert event.kind == ControlKind.BUTTON
    assert event.control_index == 0
    assert event.value == 0
    assert not event.is_pressed


def test_parse_dial_value() -> None:
    event = parse_report(bytes.fromhex("0100ff" + "00" * 61))

    assert event.kind == ControlKind.DIAL
    assert event.control_index == 0
    assert event.value == 255
    assert event.percent == 100


def test_reject_unknown_event_kind() -> None:
    try:
        parse_report(bytes.fromhex("030000"))
    except ReportParseError:
        return

    raise AssertionError("unknown event kind should fail")
