from pcpanel.config import DEFAULT_LIGHTING_COLORS


CHANNEL_COLORS = DEFAULT_LIGHTING_COLORS


APP_STYLE = """
QWidget {
    background: #0C111A;
    color: #F2F4F7;
    font-family: Inter, "Segoe UI", Arial, sans-serif;
    font-size: 13px;
}

QMainWindow {
    background: #0C111A;
}

QLabel {
    background: transparent;
}

QFrame#HeaderBar,
QFrame#SidePanel,
QFrame#ChannelStrip {
    background: #121826;
    border: 1px solid #1E2A3A;
    border-radius: 8px;
}

QFrame#ChannelStrip[muted="true"] {
    border-color: #FF5A67;
}

QFrame#ChannelStrip[unmapped="true"] {
    border-color: #1E2A3A;
}

QLabel#TargetState,
QLabel#ConfigBadge {
    background: #1E2A3A;
    border: 1px solid #1E2A3A;
    border-radius: 7px;
    color: rgba(230, 240, 255, 0.68);
    font-size: 11px;
    font-weight: 600;
    padding: 4px 7px;
}

QLabel#TargetState[state="active"] {
    background: #18302D;
    border-color: #35D0BA;
    color: #A9FFF2;
}

QLabel#TargetState[state="waiting"] {
    background: #332B18;
    border-color: #F7C948;
    color: #FFE8A3;
}

QLabel#TargetState[state="system"] {
    background: #1E2A3A;
    border-color: #0D6EFD;
    color: #E6F0FF;
}

QLabel#ConfigBadge[dirty="true"] {
    background: #332B18;
    border-color: #F7C948;
    color: #FFE8A3;
}

QLabel#Title {
    font-family: Orbitron, Rajdhani, Inter, "Segoe UI", sans-serif;
    font-size: 24px;
    font-weight: 700;
}

QLabel#ChannelTitle,
QLabel#SectionTitle,
QLabel#TargetLabel {
    font-family: Rajdhani, Inter, "Segoe UI", sans-serif;
    font-weight: 700;
}

QLabel#Subtitle,
QLabel#Meta,
QLabel#SmallText {
    color: rgba(230, 240, 255, 0.68);
}

QLabel#DeviceBadge,
QLabel#MuteBadge,
QPushButton#MuteBadge {
    background: #1E2A3A;
    border: 1px solid #1E2A3A;
    border-radius: 8px;
    padding: 6px 10px;
}

QLabel#DeviceBadge[state="connected"] {
    background: #18302D;
    border-color: #35D0BA;
    color: #A9FFF2;
}

QLabel#DeviceBadge[state="reconnecting"],
QLabel#DeviceBadge[state="starting"] {
    background: #332B18;
    border-color: #F7C948;
    color: #FFE8A3;
}

QLabel#DeviceBadge[state="stopped"] {
    background: #3A1F26;
    border-color: #FF5A67;
    color: #FFB3BA;
}

QLabel#AppChip {
    background: #1E2A3A;
    border: 1px solid #1E2A3A;
    border-radius: 8px;
    color: #F2F4F7;
    font-weight: 600;
    padding: 7px 10px;
}

QLabel#MuteBadge[muted="true"],
QPushButton#MuteBadge[muted="true"] {
    background: #3A1F26;
    border-color: #FF5A67;
    color: #FFB3BA;
}

QLabel#MuteBadge[muted="false"],
QPushButton#MuteBadge[muted="false"] {
    background: #18302D;
    border-color: #35D0BA;
    color: #A9FFF2;
}

QLabel#MuteBadge[muted="unknown"],
QPushButton#MuteBadge[muted="unknown"] {
    color: rgba(230, 240, 255, 0.38);
}

QLabel#PercentText {
    font-size: 28px;
    font-weight: 700;
}

QProgressBar {
    background: #1E2A3A;
    border: 1px solid #1E2A3A;
    border-radius: 6px;
    color: transparent;
}

QProgressBar::chunk {
    border-radius: 5px;
}

QComboBox,
QPushButton,
QCheckBox {
    background: #1E2A3A;
    border: 1px solid #1E2A3A;
    border-radius: 6px;
    color: #F2F4F7;
    padding: 7px 9px;
}

QPushButton#ColorSwatch {
    border: 1px solid #1E2A3A;
    border-radius: 6px;
    padding: 0;
}

QPushButton#ColorSwatch:disabled {
    border-color: #1E2A3A;
}

QComboBox:hover,
QPushButton:hover {
    border-color: #4FC3FF;
}

QPushButton:pressed {
    background: #1E2A3A;
}

QPushButton#PrimaryButton:enabled {
    background: #0D6EFD;
    border-color: #4FC3FF;
    color: #F2F4F7;
    font-weight: 700;
}

QPushButton:disabled {
    background: #121826;
    border-color: #1E2A3A;
    color: rgba(230, 240, 255, 0.38);
}

QComboBox:focus,
QPushButton:focus,
QCheckBox:focus {
    border-color: #4FC3FF;
}

QComboBox QAbstractItemView {
    background: #121826;
    border: 1px solid #1E2A3A;
    color: #F2F4F7;
    selection-background-color: #0D6EFD;
}

QStatusBar {
    background: #0C111A;
    color: rgba(230, 240, 255, 0.68);
}
"""
