from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_udev_rule_is_scoped_to_supported_device() -> None:
    rule = (ROOT / "packaging" / "99-pcpanel.rules").read_text(encoding="utf-8")

    assert 'ATTR{idVendor}=="0483"' in rule
    assert 'ATTR{idProduct}=="a3c4"' in rule
    assert 'TAG+="uaccess"' in rule


def test_desktop_launcher_checks_installed_executable() -> None:
    launcher = (ROOT / "packaging" / "pcpanel-gui.desktop").read_text(encoding="utf-8")

    assert "Exec=__EXEC_PATH__" in launcher
    assert "TryExec=__EXEC_PATH__" in launcher


def test_pyinstaller_collects_lazy_pulsectl_import() -> None:
    spec = (ROOT / "pcpanel-gui.spec").read_text(encoding="utf-8")

    assert 'collect_submodules("pulsectl")' in spec
