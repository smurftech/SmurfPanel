from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from pcpanel.autostart import autostart_path
from pcpanel.audio import OutputDevice
from pcpanel.config import ButtonAction, DialTarget
from pcpanel.events import ControlEvent, ControlKind
from pcpanel.gui.resources import resource_path


class ChannelStrip(QFrame):
    options_clicked = Signal(int)
    mute_clicked = Signal(int)
    led_toggled = Signal(int, bool)
    led_color_clicked = Signal(int)

    def __init__(self, index: int, accent: str) -> None:
        super().__init__()
        self.index = index
        self.accent = accent
        self.setObjectName("ChannelStrip")
        self.setProperty("muted", False)
        self.setProperty("unmapped", False)
        self.setMinimumWidth(170)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        self.accent_line = QFrame()
        self.accent_line.setFixedHeight(4)
        self.accent_line.setStyleSheet(f"background: {accent}; border-radius: 2px;")
        layout.addWidget(self.accent_line)

        self.title = QLabel(f"Dial {index + 1}")
        self.title.setStyleSheet("font-size: 16px; font-weight: 700;")
        layout.addWidget(self.title)

        self.target_label = QLabel("None")
        self.target_label.setObjectName("Subtitle")
        self.target_label.setWordWrap(True)
        layout.addWidget(self.target_label)

        self.meter = QProgressBar()
        self.meter.setOrientation(Qt.Orientation.Vertical)
        self.meter.setRange(0, 100)
        self.meter.setValue(0)
        self.meter.setFixedHeight(150)
        self.meter.setTextVisible(False)
        self.meter.setStyleSheet(f"QProgressBar::chunk {{ background: {accent}; }}")
        layout.addWidget(self.meter, 1)

        self.percent = QLabel("--%")
        self.percent.setObjectName("PercentText")
        self.percent.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.percent)

        self.mute = QPushButton("Mute: --")
        self.mute.setObjectName("MuteBadge")
        self.mute.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mute.clicked.connect(lambda: self.mute_clicked.emit(self.index))
        layout.addWidget(self.mute)

        lower_row = QHBoxLayout()
        lower_row.setSpacing(8)
        self.options = QPushButton("Options")
        self.options.setCursor(Qt.CursorShape.PointingHandCursor)
        self.options.clicked.connect(lambda: self.options_clicked.emit(self.index))
        lower_row.addWidget(self.options)
        lower_row.addStretch(1)
        self.led_enabled = QCheckBox("LED")
        self.led_enabled.toggled.connect(
            lambda enabled: self.led_toggled.emit(self.index, enabled)
        )
        self.led_color = QPushButton()
        self.led_color.setObjectName("ColorSwatch")
        self.led_color.setFixedSize(34, 28)
        self.led_color.setCursor(Qt.CursorShape.PointingHandCursor)
        self.led_color.setToolTip("Choose LED color")
        self.led_color.clicked.connect(lambda: self.led_color_clicked.emit(self.index))
        lower_row.addWidget(self.led_enabled)
        lower_row.addWidget(self.led_color)
        layout.addLayout(lower_row)

        self.raw = QLabel("raw: --")
        self.raw.setObjectName("SmallText")
        self.raw.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.raw.setVisible(False)
        layout.addWidget(self.raw)

    def set_led_state(self, enabled: bool, color: str) -> None:
        self.led_enabled.blockSignals(True)
        self.led_enabled.setChecked(enabled)
        self.led_enabled.blockSignals(False)
        self.led_color.setEnabled(enabled)
        border = "#303842" if enabled else "#252D35"
        self.led_color.setStyleSheet(
            "QPushButton#ColorSwatch { "
            f"background: {color}; border: 1px solid {border}; border-radius: 6px; padding: 0; "
            "}"
        )
        self.led_color.setToolTip(f"Choose LED color ({color})")

    def set_debug_visible(self, visible: bool) -> None:
        self.raw.setVisible(visible)

    def set_event(self, event: ControlEvent) -> None:
        self.raw.setText(f"raw: {event.raw[:12]}")
        if event.kind == ControlKind.DIAL:
            self.set_volume_state(event.percent)

    def set_volume_state(self, percent: int | None) -> None:
        if percent is None:
            self.meter.setValue(0)
            self.percent.setText("--%")
            return
        percent = max(0, min(100, percent))
        self.meter.setValue(percent)
        self.percent.setText(f"{percent}%")

    def set_target_label(self, target: DialTarget) -> None:
        self.target_label.setText(target.label)
        self.setProperty("unmapped", target.type == "none")
        self._refresh_style()

    def set_mute_state(self, muted: bool | None) -> None:
        if muted is None:
            self.mute.setText("Mute: --")
            self.mute.setProperty("muted", "unknown")
            self.setProperty("muted", False)
        elif muted:
            self.mute.setText("Muted")
            self.mute.setProperty("muted", "true")
            self.setProperty("muted", True)
        else:
            self.mute.setText("Unmuted")
            self.mute.setProperty("muted", "false")
            self.setProperty("muted", False)
        self._refresh_style()
        self.mute.style().unpolish(self.mute)
        self.mute.style().polish(self.mute)

    def _refresh_style(self) -> None:
        self.style().unpolish(self)
        self.style().polish(self)


class StreamList(QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("SidePanel")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)
        self.title = QLabel("Active Apps")
        self.title.setStyleSheet("font-size: 16px; font-weight: 700;")
        self.empty = QLabel("No active streams")
        self.empty.setObjectName("Meta")
        layout.addWidget(self.title)
        layout.addWidget(self.empty)
        layout.addStretch(1)
        self._layout = layout
        self._rows: list[QWidget] = []

    def set_streams(self, streams) -> None:
        for row in self._rows:
            self._layout.removeWidget(row)
            row.deleteLater()
        self._rows = []
        self.empty.setVisible(not streams)
        for stream in streams:
            chip = QLabel(stream.name)
            chip.setObjectName("AppChip")
            chip.setToolTip(stream.binary or stream.name)
            self._layout.insertWidget(self._layout.count() - 1, chip)
            self._rows.append(chip)


class DialOptionsDialog(QDialog):
    def __init__(
        self,
        parent: QWidget,
        dial_number: int,
        current_target: DialTarget,
        current_action: ButtonAction,
        target_options: list[tuple[str, DialTarget]],
        output_devices: list[OutputDevice],
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Dial {dial_number} options")
        self.setModal(True)
        self._target_options = target_options
        self._output_devices = output_devices

        layout = QVBoxLayout(self)
        self.form = QFormLayout()
        self.form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

        self.target = QComboBox()
        self._populate_target_combo(current_target)
        self.form.addRow("Dial target", self.target)

        self.button_action = QComboBox()
        self.button_action.addItem("Mute/unmute", "mute")
        self.button_action.addItem("Set output", "set_output")
        self.button_action.addItem("Toggle outputs", "toggle_output")
        self._set_combo_to_data(self.button_action, current_action.type)
        self.button_action.currentIndexChanged.connect(self._sync_action_visibility)
        self.form.addRow("Press action", self.button_action)

        self.output_label = QLabel("Device")
        self.output = QComboBox()
        self._populate_output_combo(
            self.output,
            current_action.output_name,
            current_action.output_label,
        )
        self.form.addRow(self.output_label, self.output)

        self.toggle_output_label = QLabel("Device 2")
        self.toggle_output = QComboBox()
        self._populate_output_combo(
            self.toggle_output,
            current_action.toggle_output_name,
            current_action.toggle_output_label,
        )
        self.form.addRow(self.toggle_output_label, self.toggle_output)

        layout.addLayout(self.form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Ok
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.adjustSize()
        self.setFixedSize(self.sizeHint())
        self._sync_action_visibility()

    def selected_target(self) -> DialTarget:
        target = self.target.currentData()
        if isinstance(target, DialTarget):
            return target
        return DialTarget()

    def selected_button_action(self) -> ButtonAction:
        action_type = self.button_action.currentData()
        output_name = self.output.currentData()
        toggle_output_name = self.toggle_output.currentData()
        if action_type not in ("mute", "set_output", "toggle_output"):
            action_type = "mute"
        if action_type == "mute":
            output_name = None
            toggle_output_name = None
        elif action_type == "set_output":
            toggle_output_name = None
        return ButtonAction(
            type=action_type,
            output_name=output_name if isinstance(output_name, str) else None,
            output_label=self.output.currentText() if isinstance(output_name, str) else None,
            toggle_output_name=toggle_output_name if isinstance(toggle_output_name, str) else None,
            toggle_output_label=self.toggle_output.currentText() if isinstance(toggle_output_name, str) else None,
        )

    def _populate_target_combo(self, current_target: DialTarget) -> None:
        current_key = _target_key(current_target)
        selected_index = 0
        for index, (label, target) in enumerate(self._target_options):
            self.target.addItem(label, target)
            if _target_key(target) == current_key:
                selected_index = index
        if current_key not in {_target_key(target) for _, target in self._target_options}:
            self.target.addItem(f"{current_target.label} (saved)", current_target)
            selected_index = self.target.count() - 1
        self.target.setCurrentIndex(selected_index)

    def _populate_output_combo(
        self,
        combo: QComboBox,
        current_name: str | None,
        current_label: str | None,
    ) -> None:
        combo.addItem("Choose output", None)
        selected_index = 0
        for index, device in enumerate(self._output_devices, start=1):
            combo.addItem(device.label, device.name)
            if device.name == current_name:
                selected_index = index
        if current_name and selected_index == 0:
            combo.addItem(f"{current_label or current_name} (saved)", current_name)
            selected_index = combo.count() - 1
        combo.setCurrentIndex(selected_index)

    def _sync_action_visibility(self) -> None:
        action_type = self.button_action.currentData()
        self.output_label.setText("Device 1" if action_type == "toggle_output" else "Device")
        show_first_output = action_type in ("set_output", "toggle_output")
        show_second_output = action_type == "toggle_output"
        self.output_label.setVisible(show_first_output)
        self.output.setVisible(show_first_output)
        self.toggle_output_label.setVisible(show_second_output)
        self.toggle_output.setVisible(show_second_output)

    def _set_combo_to_data(self, combo: QComboBox, value: object) -> None:
        for index in range(combo.count()):
            if combo.itemData(index) == value:
                combo.setCurrentIndex(index)
                return
        combo.setCurrentIndex(0)


def _target_key(target: DialTarget) -> tuple[str, str | None, str | None, str]:
    return (target.type, target.app_name, target.binary, target.label)


class AboutDialog(QDialog):
    def __init__(self, parent: QWidget, version: str, config_path: str) -> None:
        super().__init__(parent)
        self.setWindowTitle("About PCPanel")
        self.setModal(True)
        self.setFixedWidth(520)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 18)
        layout.setSpacing(16)

        header = QHBoxLayout()
        header.setSpacing(14)
        logo = QLabel()
        logo.setPixmap(QPixmap(str(resource_path("assets/pcpanel.svg"))).scaled(
            72,
            72,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        ))
        header.addWidget(logo)

        title_stack = QVBoxLayout()
        title = QLabel("PCPanel")
        title.setStyleSheet("font-size: 24px; font-weight: 700;")
        subtitle = QLabel("USB audio control surface for Linux")
        subtitle.setObjectName("Subtitle")
        creator = QLabel('Created by <a href="https://www.smurftech.com">Smurftech</a>')
        creator.setOpenExternalLinks(True)
        creator.setObjectName("Subtitle")
        title_stack.addWidget(title)
        title_stack.addWidget(subtitle)
        title_stack.addWidget(creator)
        header.addLayout(title_stack, 1)
        layout.addLayout(header)

        form = QFormLayout()
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        form.addRow("Version", QLabel(version))
        form.addRow("Website", _link_label("www.smurftech.com", "https://www.smurftech.com"))
        form.addRow("Supported device", QLabel("PCPanel Mini (0483:a3c4)"))
        form.addRow("Audio backend", QLabel("pactl / PulseAudio or PipeWire"))
        form.addRow("Config", _path_label(_display_path(config_path)))
        form.addRow("Startup", _path_label(_display_path(autostart_path())))
        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)


def _link_label(text: str, url: str) -> QLabel:
    label = QLabel(f'<a href="{url}">{text}</a>')
    label.setOpenExternalLinks(True)
    return label


def _path_label(path: str) -> QLabel:
    label = QLabel(path)
    label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    label.setWordWrap(True)
    return label


def _display_path(path: str | Path) -> str:
    path = Path(path).expanduser()
    try:
        return f"~/{path.relative_to(Path.home())}"
    except ValueError:
        return str(path)
