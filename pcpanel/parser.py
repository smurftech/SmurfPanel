from __future__ import annotations

from pcpanel.events import ControlEvent, ControlKind, new_event


class ReportParseError(ValueError):
    pass


def parse_report(report: bytes) -> ControlEvent:
    """Parse the PCPanel event format documented in the archived mapping notes.

    The known device reports encode the useful fields in the first six hex
    characters:
      char 2: 1=dial, 2=button
      char 4: control index 0..3
      chars 5-6: value 0..255
    """
    if len(report) < 3:
        raise ReportParseError(f"Report too short: {len(report)} bytes")

    raw = report.hex()
    first6 = raw[:6]
    kind_char = first6[1]
    control_char = first6[3]
    value_hex = first6[4:6]

    if kind_char == "1":
        kind = ControlKind.DIAL
    elif kind_char == "2":
        kind = ControlKind.BUTTON
    else:
        raise ReportParseError(f"Unknown event type nibble: {kind_char!r}")

    try:
        control_index = int(control_char, 16)
        value = int(value_hex, 16)
    except ValueError as exc:
        raise ReportParseError(f"Invalid report header: {first6}") from exc

    if control_index > 3:
        raise ReportParseError(f"Control index out of range: {control_index}")

    return new_event(kind=kind, control_index=control_index, value=value, raw=raw)
