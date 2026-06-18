from __future__ import annotations

import logging
import re

import usb.core

LOGGER = logging.getLogger(__name__)

HID_SET_REPORT_REQUEST_TYPE = 0x21
HID_SET_REPORT = 0x09
HID_OUTPUT_REPORT_ID_0 = 0x0200
INTERFACE_NUMBER = 0
PACKET_SIZE = 64

MINI_PREFIX = 0x06
MINI_CUSTOM_KNOB = 0x02
COLOR_STATIC = 0x01

HEX_COLOR_RE = re.compile(r"^#?[0-9a-fA-F]{6}$")


class LightingError(RuntimeError):
    pass


def build_mini_dial_colors(colors: list[str]) -> bytes:
    payload = bytearray([MINI_PREFIX, MINI_CUSTOM_KNOB])
    for color in colors[:4]:
        payload.extend([COLOR_STATIC, *_parse_hex_color(color), 0, 0, 0])
    while len(payload) < PACKET_SIZE:
        payload.append(0)
    return bytes(payload[:PACKET_SIZE])


def send_output_report(device, payload: bytes) -> None:
    if len(payload) > PACKET_SIZE:
        raise LightingError(f"Lighting payload is too long: {len(payload)} bytes")
    report = payload + bytes(PACKET_SIZE - len(payload))
    written = device.ctrl_transfer(
        HID_SET_REPORT_REQUEST_TYPE,
        HID_SET_REPORT,
        HID_OUTPUT_REPORT_ID_0,
        INTERFACE_NUMBER,
        report,
        timeout=1000,
    )
    if written != PACKET_SIZE:
        raise LightingError(f"Lighting report wrote {written} of {PACKET_SIZE} bytes")


def colors_for_device(dials) -> list[str]:
    colors: list[str] = []
    for dial in dials[:4]:
        colors.append(dial.color if dial.enabled else "#000000")
    return colors


def _parse_hex_color(color: str) -> tuple[int, int, int]:
    if not HEX_COLOR_RE.match(color):
        LOGGER.warning("Invalid LED color %r; using black", color)
        return (0, 0, 0)
    value = color[1:] if color.startswith("#") else color
    return (
        int(value[0:2], 16),
        int(value[2:4], 16),
        int(value[4:6], 16),
    )
