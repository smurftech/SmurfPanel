from __future__ import annotations

import logging

LOGGER = logging.getLogger(__name__)


class Osd:
    def show_volume(self, label: str, percent: int, control_index: int | None = None) -> None:
        ...

    def show_mute(self, label: str, control_index: int | None = None) -> None:
        ...


class LoggingOsd:
    def show_volume(self, label: str, percent: int, control_index: int | None = None) -> None:
        LOGGER.info("%s volume %s%%", label, percent)

    def show_mute(self, label: str, control_index: int | None = None) -> None:
        LOGGER.info("%s mute toggled", label)
