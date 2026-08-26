from __future__ import annotations

import sys
import logging
from pathlib import Path

from PySide6.QtGui import QFontDatabase, QIcon


LOGGER = logging.getLogger(__name__)

BRAND_FONT_FILES = (
    "assets/fonts/inter/Inter.ttf",
    "assets/fonts/orbitron/Orbitron.ttf",
    "assets/fonts/rajdhani/Rajdhani-Regular.ttf",
    "assets/fonts/rajdhani/Rajdhani-Bold.ttf",
)


def resource_path(relative_path: str) -> Path:
    bundle_root = getattr(sys, "_MEIPASS", None)
    if bundle_root:
        return Path(bundle_root) / relative_path
    return Path(__file__).resolve().parents[1] / relative_path


def app_icon() -> QIcon:
    return QIcon(str(resource_path("assets/pcpanel.svg")))


def load_brand_fonts() -> set[str]:
    """Register bundled brand fonts and return their resolved family names."""
    families: set[str] = set()
    for relative_path in BRAND_FONT_FILES:
        font_id = QFontDatabase.addApplicationFont(str(resource_path(relative_path)))
        if font_id < 0:
            LOGGER.warning("Unable to load bundled font: %s", relative_path)
            continue
        families.update(QFontDatabase.applicationFontFamilies(font_id))
    return families
