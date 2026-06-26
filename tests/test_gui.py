from pcpanel.config import ButtonAction
from pcpanel.gui.app import button_action_label, reader_status_text
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
