from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from time import monotonic


class ControlKind(str, Enum):
    DIAL = "dial"
    BUTTON = "button"


@dataclass(frozen=True)
class ControlEvent:
    kind: ControlKind
    control_index: int
    value: int
    raw: str
    received_at: float

    @property
    def control_number(self) -> int:
        return self.control_index + 1

    @property
    def percent(self) -> int:
        return round(self.value * 100 / 255)

    @property
    def is_pressed(self) -> bool:
        return self.value != 0


def new_event(kind: ControlKind, control_index: int, value: int, raw: str) -> ControlEvent:
    return ControlEvent(
        kind=kind,
        control_index=control_index,
        value=value,
        raw=raw,
        received_at=monotonic(),
    )
