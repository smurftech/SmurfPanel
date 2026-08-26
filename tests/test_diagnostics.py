import usb.core

from pcpanel.diagnostics import format_diagnostics, run_diagnostics


def test_diagnostics_report_ready_system(monkeypatch) -> None:
    monkeypatch.setattr("pcpanel.diagnostics.shutil.which", lambda _name: "/usr/bin/pactl")
    monkeypatch.setattr("pcpanel.diagnostics.usb.core.find", lambda **_kwargs: object())

    checks = run_diagnostics()

    assert all(check.ok for check in checks)
    assert format_diagnostics(checks) == (
        "PASS pactl: pactl command found\nPASS usb: PCPanel Mini USB device detected"
    )


def test_diagnostics_report_missing_requirements(monkeypatch) -> None:
    monkeypatch.setattr("pcpanel.diagnostics.shutil.which", lambda _name: None)
    monkeypatch.setattr("pcpanel.diagnostics.usb.core.find", lambda **_kwargs: None)

    checks = run_diagnostics()

    assert [check.ok for check in checks] == [False, False]
    assert "FAIL pactl" in format_diagnostics(checks)
    assert "FAIL usb" in format_diagnostics(checks)


def test_diagnostics_report_usb_lookup_error(monkeypatch) -> None:
    monkeypatch.setattr("pcpanel.diagnostics.shutil.which", lambda _name: "/usr/bin/pactl")

    def fail_usb_lookup(**_kwargs):
        raise usb.core.USBError("access denied")

    monkeypatch.setattr("pcpanel.diagnostics.usb.core.find", fail_usb_lookup)

    checks = run_diagnostics()

    assert checks[1].name == "usb"
    assert checks[1].ok is False
    assert "access denied" in checks[1].message
