from pcpanel.config import DEFAULT_LIGHTING_COLORS
from pcpanel.gui.brand_tokens import style_tokens


CHANNEL_COLORS = DEFAULT_LIGHTING_COLORS


APP_STYLE = """
QWidget {
    background: %(deep_night)s;
    color: %(clean_white)s;
    font-family: Inter, "Segoe UI", Arial, sans-serif;
    font-size: 13px;
}

QMainWindow {
    background: %(deep_night)s;
}

QLabel {
    background: transparent;
}

QFrame#HeaderBar,
QFrame#SidePanel,
QFrame#ChannelStrip {
    background: %(night_slate)s;
    border: 1px solid %(border_default)s;
    border-radius: %(radius_medium)s;
}

QFrame#ChannelStrip[muted="true"] {
    border-color: %(danger_border)s;
}

QFrame#ChannelStrip[unmapped="true"] {
    border-color: %(border_default)s;
}

QLabel#TargetState,
QLabel#ConfigBadge {
    background: %(steel_blue)s;
    border: 1px solid %(border_default)s;
    border-radius: 7px;
    color: %(muted_text)s;
    font-size: 11px;
    font-weight: 600;
    padding: 4px 7px;
}

QLabel#TargetState[state="active"] {
    background: %(success_surface)s;
    border-color: %(success_border)s;
    color: %(success_text)s;
}

QLabel#TargetState[state="waiting"] {
    background: %(warning_surface)s;
    border-color: %(warning_border)s;
    color: %(warning_text)s;
}

QLabel#TargetState[state="system"] {
    background: %(steel_blue)s;
    border-color: %(electric_blue)s;
    color: %(ice_blue)s;
}

QLabel#ConfigBadge[dirty="true"] {
    background: %(warning_surface)s;
    border-color: %(warning_border)s;
    color: %(warning_text)s;
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
    color: %(muted_text)s;
}

QLabel#DeviceBadge,
QLabel#MuteBadge,
QPushButton#MuteBadge {
    background: %(steel_blue)s;
    border: 1px solid %(border_default)s;
    border-radius: %(radius_medium)s;
    padding: 6px 10px;
}

QLabel#DeviceBadge[state="connected"] {
    background: %(success_surface)s;
    border-color: %(success_border)s;
    color: %(success_text)s;
}

QLabel#DeviceBadge[state="reconnecting"],
QLabel#DeviceBadge[state="starting"] {
    background: %(warning_surface)s;
    border-color: %(warning_border)s;
    color: %(warning_text)s;
}

QLabel#DeviceBadge[state="stopped"] {
    background: %(danger_surface)s;
    border-color: %(danger_border)s;
    color: %(danger_text)s;
}

QLabel#AppChip {
    background: %(steel_blue)s;
    border: 1px solid %(border_default)s;
    border-radius: %(radius_medium)s;
    color: %(clean_white)s;
    font-weight: 600;
    padding: 7px 10px;
}

QLabel#MuteBadge[muted="true"],
QPushButton#MuteBadge[muted="true"] {
    background: %(danger_surface)s;
    border-color: %(danger_border)s;
    color: %(danger_text)s;
}

QLabel#MuteBadge[muted="false"],
QPushButton#MuteBadge[muted="false"] {
    background: %(success_surface)s;
    border-color: %(success_border)s;
    color: %(success_text)s;
}

QLabel#MuteBadge[muted="unknown"],
QPushButton#MuteBadge[muted="unknown"] {
    color: %(disabled_text)s;
}

QLabel#PercentText {
    font-size: 28px;
    font-weight: 700;
}

QProgressBar {
    background: %(steel_blue)s;
    border: 1px solid %(border_default)s;
    border-radius: %(radius_small)s;
    color: transparent;
}

QProgressBar::chunk {
    border-radius: 5px;
}

QComboBox,
QPushButton,
QCheckBox {
    background: %(steel_blue)s;
    border: 1px solid %(border_default)s;
    border-radius: %(radius_small)s;
    color: %(clean_white)s;
    padding: 7px 9px;
}

QPushButton#ColorSwatch {
    border: 1px solid %(border_default)s;
    border-radius: %(radius_small)s;
    padding: 0;
}

QPushButton#ColorSwatch:disabled {
    border-color: %(border_default)s;
}

QComboBox:hover,
QPushButton:hover {
    border-color: %(cyan_accent)s;
}

QPushButton:pressed {
    background: %(steel_blue)s;
}

QPushButton#PrimaryButton:enabled {
    background: %(electric_blue)s;
    border-color: %(cyan_accent)s;
    color: %(clean_white)s;
    font-weight: 700;
}

QPushButton:disabled {
    background: %(night_slate)s;
    border-color: %(border_default)s;
    color: %(disabled_text)s;
}

QComboBox:focus,
QPushButton:focus,
QCheckBox:focus {
    border-color: %(cyan_accent)s;
}

QComboBox QAbstractItemView {
    background: %(night_slate)s;
    border: 1px solid %(border_default)s;
    color: %(clean_white)s;
    selection-background-color: %(electric_blue)s;
}

QStatusBar {
    background: %(deep_night)s;
    color: %(muted_text)s;
}
""" % style_tokens()
