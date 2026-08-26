from __future__ import annotations

import shutil
from dataclasses import dataclass

import usb.core

from pcpanel.usb_reader import PRODUCT_ID, VENDOR_ID


@dataclass(frozen=True)
class DiagnosticCheck:
    name: str
    ok: bool
    message: str


def run_diagnostics() -> list[DiagnosticCheck]:
    pactl_path = shutil.which("pactl")
    checks = [
        DiagnosticCheck(
            name="pactl",
            ok=pactl_path is not None,
            message=(
                "pactl command found"
                if pactl_path is not None
                else "pactl is missing; install PulseAudio utilities for audio diagnostics"
            ),
        )
    ]
    try:
        device = usb.core.find(idVendor=VENDOR_ID, idProduct=PRODUCT_ID)
    except usb.core.USBError as exc:
        checks.append(DiagnosticCheck("usb", False, f"USB lookup failed: {exc}"))
    else:
        checks.append(
            DiagnosticCheck(
                name="usb",
                ok=device is not None,
                message=(
                    "PCPanel Mini USB device detected"
                    if device is not None
                    else "PCPanel Mini USB device not detected; connect it and run diagnostics again"
                ),
            )
        )
    return checks


def format_diagnostics(checks: list[DiagnosticCheck]) -> str:
    return "\n".join(
        f"{'PASS' if check.ok else 'FAIL'} {check.name}: {check.message}"
        for check in checks
    )
