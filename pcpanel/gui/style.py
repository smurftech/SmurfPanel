CHANNEL_COLORS = ["#4DA3FF", "#35D0BA", "#A78BFA", "#F7C948"]


APP_STYLE = """
QWidget {
    background: #101316;
    color: #F2F5F7;
    font-family: Inter, "Segoe UI", Arial, sans-serif;
    font-size: 13px;
}

QMainWindow {
    background: #101316;
}

QLabel {
    background: transparent;
}

QFrame#HeaderBar,
QFrame#SidePanel,
QFrame#ChannelStrip {
    background: #181D22;
    border: 1px solid #303842;
    border-radius: 8px;
}

QFrame#ChannelStrip[muted="true"] {
    border-color: #FF5A67;
}

QFrame#ChannelStrip[unmapped="true"] {
    border-color: #252D35;
}

QLabel#Title {
    font-size: 24px;
    font-weight: 700;
}

QLabel#Subtitle,
QLabel#Meta,
QLabel#SmallText {
    color: #98A4AF;
}

QLabel#DeviceBadge,
QLabel#MuteBadge,
QPushButton#MuteBadge {
    background: #20262D;
    border: 1px solid #303842;
    border-radius: 8px;
    padding: 6px 10px;
}

QLabel#AppChip {
    background: #20262D;
    border: 1px solid #303842;
    border-radius: 8px;
    color: #F2F5F7;
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
    color: #66727D;
}

QLabel#PercentText {
    font-size: 28px;
    font-weight: 700;
}

QProgressBar {
    background: #20262D;
    border: 1px solid #303842;
    border-radius: 6px;
    color: transparent;
}

QProgressBar::chunk {
    border-radius: 5px;
}

QComboBox,
QPushButton,
QCheckBox {
    background: #20262D;
    border: 1px solid #303842;
    border-radius: 6px;
    color: #F2F5F7;
    padding: 7px 9px;
}

QComboBox:hover,
QPushButton:hover {
    border-color: #4DA3FF;
}

QPushButton:pressed {
    background: #26313A;
}

QComboBox QAbstractItemView {
    background: #181D22;
    border: 1px solid #303842;
    color: #F2F5F7;
    selection-background-color: #26313A;
}

QStatusBar {
    background: #101316;
    color: #98A4AF;
}
"""
