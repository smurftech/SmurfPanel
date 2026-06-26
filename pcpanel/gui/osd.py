from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from pcpanel.gui.style import CHANNEL_COLORS

OSD_HIDE_DELAY_MS = 1800
OSD_WIDTH = 360
OSD_ROW_HEIGHT = 74
OSD_MARGIN = 28


class DialOsd:
    def __init__(self) -> None:
        self.window = QWidget()
        self.window.setWindowFlags(
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.window.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.window.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.window.setFixedWidth(OSD_WIDTH)

        self.layout = QVBoxLayout(self.window)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(8)

        self.rows = [OsdRow(index, CHANNEL_COLORS[index]) for index in range(4)]
        self.timers: list[QTimer] = []
        for row in self.rows:
            row.hide()
            self.layout.addWidget(row)
            timer = QTimer(self.window)
            timer.setSingleShot(True)
            timer.timeout.connect(lambda row=row: self._hide_row(row))
            self.timers.append(timer)

    def show_volume(self, label: str, percent: int, control_index: int | None = None) -> None:
        if control_index is None or not 0 <= control_index < len(self.rows):
            control_index = 0
        row = self.rows[control_index]
        row.set_volume(label, percent)
        row.show()
        self.timers[control_index].start(OSD_HIDE_DELAY_MS)
        self._place_window()
        self.window.show()
        self.window.raise_()

    def show_mute(self, label: str, control_index: int | None = None) -> None:
        if control_index is None or not 0 <= control_index < len(self.rows):
            return
        row = self.rows[control_index]
        row.set_message(label)
        row.show()
        self.timers[control_index].start(OSD_HIDE_DELAY_MS)
        self._place_window()
        self.window.show()
        self.window.raise_()

    def hide(self) -> None:
        self.window.hide()

    def _hide_row(self, row: "OsdRow") -> None:
        row.hide()
        self._hide_if_empty()

    def _hide_if_empty(self) -> None:
        if not any(row.isVisible() for row in self.rows):
            self.window.hide()
            return
        self._place_window()

    def _place_window(self) -> None:
        self.window.adjustSize()
        screen = QApplication.primaryScreen()
        if screen is None:
            return
        available = screen.availableGeometry()
        x = available.right() - self.window.width() - OSD_MARGIN
        y = available.bottom() - self.window.height() - OSD_MARGIN
        self.window.move(x, y)


class OsdRow(QFrame):
    def __init__(self, index: int, accent: str) -> None:
        super().__init__()
        self.index = index
        self.accent = accent
        self.setObjectName("OsdRow")
        self.setFixedHeight(OSD_ROW_HEIGHT)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.setStyleSheet(
            "QFrame#OsdRow {"
            "background: rgba(16, 19, 22, 224);"
            "border: 1px solid #303842;"
            "border-radius: 8px;"
            "}"
            "QLabel { background: transparent; color: #F2F5F7; }"
            "QLabel#OsdMeta { color: #98A4AF; font-size: 11px; }"
            "QLabel#OsdPercent { font-size: 18px; font-weight: 700; }"
            "QProgressBar {"
            "background: #20262D;"
            "border: 1px solid #303842;"
            "border-radius: 5px;"
            "color: transparent;"
            "height: 10px;"
            "}"
            f"QProgressBar::chunk {{ background: {accent}; border-radius: 4px; }}"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        top = QHBoxLayout()
        top.setSpacing(8)
        self.title = QLabel(f"Dial {index + 1}")
        self.title.setObjectName("OsdMeta")
        self.label = QLabel("None")
        self.label.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        self.percent = QLabel("--%")
        self.percent.setObjectName("OsdPercent")
        self.percent.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        top.addWidget(self.title)
        top.addWidget(self.label, 1)
        top.addWidget(self.percent)
        layout.addLayout(top)

        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        self.bar.setTextVisible(False)
        layout.addWidget(self.bar)

    def set_volume(self, label: str, percent: int) -> None:
        percent = max(0, min(100, percent))
        self.label.setText(label)
        self.percent.setText(f"{percent}%")
        self.bar.setValue(percent)

    def set_message(self, label: str) -> None:
        self.label.setText(label)
        self.percent.setText("")
