from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from PySide6.QtCore import QObject, QTimer, Qt, Signal, Slot
from PySide6.QtGui import QAction, QColor
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QColorDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QMenu,
    QPushButton,
    QStatusBar,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from pcpanel.audio import AudioStream, PactlAudioBackend
from pcpanel.config import AppConfig, DialTarget, default_config_path, load_config, save_config
from pcpanel.controller import Controller
from pcpanel.device_service import DeviceService, DeviceState, DeviceStatus
from pcpanel.events import ControlEvent, ControlKind
from pcpanel.gui.resources import app_icon
from pcpanel.gui.style import APP_STYLE, CHANNEL_COLORS
from pcpanel.gui.widgets import ChannelStrip, StreamList
from pcpanel.lighting import build_mini_dial_colors, colors_for_device


LOGGER = logging.getLogger(__name__)
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720


class EventBridge(QObject):
    event_received = Signal(object)
    device_state_received = Signal(object)


class MainWindow(QMainWindow):
    def __init__(self, config_path: Path) -> None:
        super().__init__()
        self.config_path = config_path
        self.config = load_config(config_path)
        self.audio = PactlAudioBackend()
        self.controller = Controller(config=self.config, audio=self.audio)
        self.bridge = EventBridge()
        self.device_service: DeviceService | None = None
        self.streams: list[AudioStream] = []
        self.rows = [ChannelStrip(index, CHANNEL_COLORS[index]) for index in range(4)]
        self._refreshing_targets = False
        self._allow_close = False
        self.tray_icon: QSystemTrayIcon | None = None

        self.setWindowTitle("PCPanel")
        self.setWindowIcon(app_icon())
        self.resize(WINDOW_WIDTH, WINDOW_HEIGHT)
        self.setMinimumSize(900, 560)
        self.setStatusBar(QStatusBar())
        self._build_ui()
        self._build_tray()
        self._connect_signals()

        self.refresh_streams()
        self.refresh_initial_volumes()
        self.refresh_status()
        self.start_device_service()

        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self.refresh_status)
        self.status_timer.start(1500)

        self.stream_timer = QTimer(self)
        self.stream_timer.timeout.connect(self.refresh_streams)
        self.stream_timer.start(4000)

    def _build_ui(self) -> None:
        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        header_frame = QFrame()
        header_frame.setObjectName("HeaderBar")
        header = QHBoxLayout(header_frame)
        header.setContentsMargins(14, 12, 14, 12)
        title = QLabel("PCPanel")
        title.setObjectName("Title")
        subtitle = QLabel("USB audio control surface")
        subtitle.setObjectName("Subtitle")
        title_stack = QVBoxLayout()
        title_stack.setSpacing(2)
        title_stack.addWidget(title)
        title_stack.addWidget(subtitle)

        self.device_state = QLabel("Device: starting")
        self.device_state.setObjectName("DeviceBadge")
        header.addLayout(title_stack)
        header.addStretch(1)
        header.addWidget(self.device_state)
        layout.addWidget(header_frame)

        main = QHBoxLayout()
        main.setSpacing(14)
        strips = QHBoxLayout()
        strips.setSpacing(12)
        for row in self.rows:
            strips.addWidget(row, 1)
        main.addLayout(strips, 1)
        layout.addLayout(main, 1)

        self.stream_list = StreamList()
        layout.addWidget(self.stream_list)

        controls = QHBoxLayout()
        self.osd_enabled = QCheckBox("OSD enabled")
        self.osd_enabled.setChecked(self.config.osd_enabled)
        self.debug_enabled = QCheckBox("Debug reports")
        self.refresh_button = QPushButton("Refresh apps")
        self.save_button = QPushButton("Save config")
        controls.addWidget(self.osd_enabled)
        controls.addWidget(self.debug_enabled)
        controls.addStretch(1)
        controls.addWidget(self.refresh_button)
        controls.addWidget(self.save_button)
        layout.addLayout(controls)

        self.setCentralWidget(root)

    def _connect_signals(self) -> None:
        self.bridge.event_received.connect(self.on_event_received)
        self.bridge.device_state_received.connect(self.on_device_status)
        self.refresh_button.clicked.connect(self.refresh_streams)
        self.save_button.clicked.connect(self.save_current_config)
        self.osd_enabled.toggled.connect(self.on_osd_toggled)
        self.debug_enabled.toggled.connect(self.on_debug_toggled)
        for index, row in enumerate(self.rows):
            row.target_changed.connect(self.on_target_changed)
            row.mute_clicked.connect(self.on_mute_clicked)
            row.led_toggled.connect(self.on_led_toggled)
            row.led_color_clicked.connect(self.on_led_color_clicked)

    def _build_tray(self) -> None:
        if not QSystemTrayIcon.isSystemTrayAvailable():
            self.statusBar().showMessage("System tray is not available")
            return

        icon = app_icon()
        self.tray_icon = QSystemTrayIcon(icon, self)
        self.tray_icon.setToolTip("PCPanel")

        menu = QMenu(self)
        show_action = QAction("Show PCPanel", self)
        hide_action = QAction("Hide to tray", self)
        quit_action = QAction("Quit", self)
        show_action.triggered.connect(self.show_from_tray)
        hide_action.triggered.connect(self.hide_to_tray)
        quit_action.triggered.connect(self.quit_from_tray)
        menu.addAction(show_action)
        menu.addAction(hide_action)
        menu.addSeparator()
        menu.addAction(quit_action)

        self.tray_icon.setContextMenu(menu)
        self.tray_icon.activated.connect(self.on_tray_activated)
        self.tray_icon.show()

    def start_device_service(self) -> None:
        self.device_service = DeviceService(
            on_event=self.bridge.event_received.emit,
            stop_event=self.controller.stop_event,
            on_state=self.bridge.device_state_received.emit,
        )
        self.device_service.start()
        self.statusBar().showMessage("USB device service started")

    @Slot(object)
    def on_device_status(self, status: DeviceStatus) -> None:
        labels = {
            DeviceState.CONNECTING: "Device: connecting",
            DeviceState.CONNECTED: "Device: connected",
            DeviceState.DISCONNECTED: "Device: disconnected",
            DeviceState.RECONNECTING: "Device: reconnecting",
            DeviceState.STOPPED: "Device: stopped",
        }
        self.device_state.setText(labels[status.state])

        if status.state == DeviceState.CONNECTED:
            self.statusBar().showMessage("PCPanel connected")
            QTimer.singleShot(100, self.apply_lighting)
            return

        if status.state == DeviceState.DISCONNECTED:
            detail = f": {status.message}" if status.message else ""
            self.statusBar().showMessage(f"PCPanel disconnected{detail}")
        elif status.state == DeviceState.RECONNECTING:
            self.statusBar().showMessage("Reconnecting to PCPanel…")
        elif status.state == DeviceState.CONNECTING:
            self.statusBar().showMessage("Connecting to PCPanel…")

    def refresh_streams(self) -> None:
        try:
            self.streams = self.audio.list_streams()
        except Exception as exc:
            self.statusBar().showMessage(f"Could not refresh app streams: {exc}")
            self.streams = []
        self.stream_list.set_streams(self.streams)
        self.rebuild_target_options()

    def rebuild_target_options(self) -> None:
        self._refreshing_targets = True
        options = self._target_options()
        for index, row in enumerate(self.rows):
            row.target.clear()
            current = self.config.dials[index]
            current_key = target_key(current)
            selected_index = 0
            for option_index, (label, target) in enumerate(options):
                row.target.addItem(label, target)
                if target_key(target) == current_key:
                    selected_index = option_index
            if current_key not in {target_key(target) for _, target in options}:
                row.target.addItem(f"{current.label} (saved)", current)
                selected_index = row.target.count() - 1
            row.target.setCurrentIndex(selected_index)
            row.set_target_label(current)
            lighting = self.config.lighting.dials[index]
            row.set_led_state(lighting.enabled, lighting.color)
        self._refreshing_targets = False

    def _target_options(self) -> list[tuple[str, DialTarget]]:
        options: list[tuple[str, DialTarget]] = [
            ("None", DialTarget(type="none", label="None")),
            ("System", DialTarget(type="system", label="System")),
        ]
        name_counts: dict[str, int] = {}
        for stream in self.streams:
            name_counts[stream.name] = name_counts.get(stream.name, 0) + 1
        for stream in self.streams:
            label = stream.name
            if name_counts[stream.name] > 1 and stream.binary:
                label = f"{stream.name} ({stream.binary})"
            options.append(
                (
                    label,
                    DialTarget(
                        type="app",
                        label=stream.name,
                        app_name=stream.name,
                        binary=stream.binary,
                        stream_id=None,
                    ),
                )
            )
        return options

    @Slot(object)
    def on_event_received(self, event: ControlEvent) -> None:
        try:
            self.controller.handle_event(event)
        except Exception as exc:
            self.statusBar().showMessage(f"Event failed: {exc}")
            LOGGER.exception("Failed to handle event")
            return

        self.rows[event.control_index].set_event(event)
        if event.kind == ControlKind.BUTTON and event.is_pressed:
            self.refresh_status()
        target = self.config.dials[event.control_index]
        self.statusBar().showMessage(
            f"{event.kind.value.title()} {event.control_number} -> {target.label} ({event.value})"
        )

    def refresh_status(self) -> None:
        try:
            system_mute = self.audio.get_system_mute()
        except Exception:
            system_mute = None
        stream_by_key = {stream_key(stream): stream for stream in self.streams}
        for index, row in enumerate(self.rows):
            target = self.config.dials[index]
            if target.type == "system":
                row.set_mute_state(system_mute)
            elif target.type == "app":
                stream = stream_by_key.get((target.app_name, target.binary))
                row.set_mute_state(stream.muted if stream else None)
            else:
                row.set_mute_state(None)
            row.set_target_label(target)

    def refresh_initial_volumes(self) -> None:
        try:
            system_volume = self.audio.get_system_volume()
        except Exception:
            system_volume = None
        stream_by_key = {stream_key(stream): stream for stream in self.streams}
        for index, row in enumerate(self.rows):
            target = self.config.dials[index]
            if target.type == "system":
                row.set_volume_state(system_volume)
            elif target.type == "app":
                stream = stream_by_key.get((target.app_name, target.binary))
                row.set_volume_state(stream.volume if stream else None)

    @Slot(int)
    def on_target_changed(self, index: int) -> None:
        if self._refreshing_targets:
            return
        target = self.rows[index].target.currentData()
        if isinstance(target, DialTarget):
            self.config.dials[index] = target
            self.controller.config = self.config
            self.rows[index].set_target_label(target)
            self.statusBar().showMessage(f"Dial {index + 1} mapped to {target.label}")
            self.refresh_status()

    @Slot(int)
    def on_mute_clicked(self, index: int) -> None:
        target = self.config.dials[index]
        if target.type == "none":
            self.statusBar().showMessage(f"Dial {index + 1} has no target")
            return
        try:
            self.audio.toggle_mute(target)
        except Exception as exc:
            self.statusBar().showMessage(f"Mute failed: {exc}")
            LOGGER.exception("Mute failed")
            return
        self.statusBar().showMessage(f"Toggled mute for {target.label}")
        self.refresh_status()

    def on_osd_toggled(self, enabled: bool) -> None:
        self.config.osd_enabled = enabled
        self.controller.config = self.config

    def on_debug_toggled(self, enabled: bool) -> None:
        for row in self.rows:
            row.set_debug_visible(enabled)

    @Slot(int, bool)
    def on_led_toggled(self, index: int, enabled: bool) -> None:
        self.config.lighting.dials[index].enabled = enabled
        lighting = self.config.lighting.dials[index]
        self.rows[index].set_led_state(lighting.enabled, lighting.color)
        self.apply_lighting()

    @Slot(int)
    def on_led_color_clicked(self, index: int) -> None:
        current = self.config.lighting.dials[index]
        selected = QColorDialog.getColor(
            QColor(current.color),
            self,
            f"Dial {index + 1} LED color",
        )
        if not selected.isValid():
            return
        current.color = selected.name().upper()
        current.enabled = True
        self.rows[index].set_led_state(current.enabled, current.color)
        self.apply_lighting()

    def apply_lighting(self) -> None:
        if not self.config.lighting.enabled:
            return
        if self.device_service is None or not self.device_service.connected:
            return
        try:
            payload = build_mini_dial_colors(colors_for_device(self.config.lighting.dials))
            self.device_service.send_output_report(payload)
        except Exception as exc:
            self.statusBar().showMessage(f"LED update failed: {exc}")
            LOGGER.debug("LED update failed", exc_info=True)
            return
        self.statusBar().showMessage("LED colors updated")

    @Slot()
    def show_from_tray(self) -> None:
        self.showNormal()
        self.raise_()
        self.activateWindow()

    @Slot()
    def hide_to_tray(self) -> None:
        self.hide()
        if self.tray_icon is not None:
            self.tray_icon.showMessage(
                "PCPanel",
                "Still running in the system tray.",
                QSystemTrayIcon.MessageIcon.Information,
                1800,
            )

    @Slot()
    def quit_from_tray(self) -> None:
        self._allow_close = True
        self.controller.stop()
        if self.tray_icon is not None:
            self.tray_icon.hide()
        QApplication.quit()

    @Slot(QSystemTrayIcon.ActivationReason)
    def on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            if self.isVisible():
                self.hide_to_tray()
            else:
                self.show_from_tray()

    def save_current_config(self) -> None:
        try:
            save_config(self.config, self.config_path)
        except Exception as exc:
            QMessageBox.critical(self, "Save failed", str(exc))
            return
        self.statusBar().showMessage(f"Saved config to {self.config_path}")

    def closeEvent(self, event) -> None:
        if self._allow_close or self.tray_icon is None:
            self.controller.stop()
            super().closeEvent(event)
            return
        event.ignore()
        self.hide_to_tray()

    def changeEvent(self, event) -> None:
        if event.type() == event.Type.WindowStateChange and self.isMinimized():
            QTimer.singleShot(0, self.hide_to_tray)
        super().changeEvent(event)


def target_key(target: DialTarget) -> tuple[str, str | None, str | None, str]:
    return (target.type, target.app_name, target.binary, target.label)


def stream_key(stream: AudioStream) -> tuple[str, str | None]:
    return (stream.name, stream.binary)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the PCPanel GUI")
    parser.add_argument("-v", "--verbose", action="store_true", help="enable debug logging")
    parser.add_argument("--config", type=Path, default=default_config_path(), help="config file path")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    app = QApplication(sys.argv)
    app.setApplicationName("PCPanel")
    app.setStyleSheet(APP_STYLE)
    window = MainWindow(config_path=args.config)
    window.setWindowState(Qt.WindowState.WindowNoState)
    window.showNormal()
    center_window(window)
    raise SystemExit(app.exec())


def center_window(window: QMainWindow) -> None:
    screen = QApplication.primaryScreen()
    if screen is None:
        return
    available = screen.availableGeometry()
    frame = window.frameGeometry()
    frame.moveCenter(available.center())
    window.move(frame.topLeft())
