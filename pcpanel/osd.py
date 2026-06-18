from __future__ import annotations

import logging

LOGGER = logging.getLogger(__name__)


class Osd:
    def show_volume(self, label: str, percent: int) -> None:
        ...

    def show_mute(self, label: str) -> None:
        ...


class LoggingOsd:
    def show_volume(self, label: str, percent: int) -> None:
        LOGGER.info("%s volume %s%%", label, percent)

    def show_mute(self, label: str) -> None:
        LOGGER.info("%s mute toggled", label)
