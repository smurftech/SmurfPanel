from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from pcpanel.config import DialTarget
from pcpanel.events import ControlEvent, ControlKind


class ChannelStrip(QFrame):
    target_changed = Signal(int)
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

        self.target = QComboBox()
        self.target.currentIndexChanged.connect(lambda _value: self.target_changed.emit(self.index))
        layout.addWidget(self.target)

        led_row = QHBoxLayout()
        led_row.setSpacing(8)
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
        led_row.addWidget(self.led_enabled)
        led_row.addStretch(1)
        led_row.addWidget(self.led_color)
        layout.addLayout(led_row)

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
