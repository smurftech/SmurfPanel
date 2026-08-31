from pathlib import Path
import os
import shutil
import subprocess


ROOT = Path(__file__).resolve().parents[1]


def test_udev_rule_is_scoped_to_supported_device() -> None:
    rule = (ROOT / "packaging" / "99-pcpanel.rules").read_text(encoding="utf-8")

    assert 'ATTR{idVendor}=="0483"' in rule
    assert 'ATTR{idProduct}=="a3c4"' in rule
    assert 'MODE="0666"' in rule
    assert 'TAG+="uaccess"' in rule


def test_desktop_launcher_checks_installed_executable() -> None:
    launcher = (ROOT / "packaging" / "pcpanel-gui.desktop").read_text(encoding="utf-8")

    assert "Exec=__EXEC_PATH__" in launcher
    assert "TryExec=__EXEC_PATH__" in launcher


def test_pyinstaller_collects_lazy_pulsectl_import() -> None:
    spec = (ROOT / "pcpanel-gui.spec").read_text(encoding="utf-8")

    assert 'collect_submodules("pulsectl")' in spec


def test_portable_installer_lifecycle_preserves_config(tmp_path: Path) -> None:
    release = tmp_path / "release"
    home = tmp_path / "home"
    data_home = home / ".local" / "share"
    (release / "app").mkdir(parents=True)
    (release / "packaging").mkdir()
    (release / "pcpanel" / "assets").mkdir(parents=True)

    executable = release / "app" / "pcpanel-gui"
    executable.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    executable.chmod(0o755)
    shutil.copy(ROOT / "scripts" / "install_desktop.sh", release / "install.sh")
    shutil.copy(ROOT / "scripts" / "uninstall_desktop.sh", release / "uninstall.sh")
    shutil.copy(ROOT / "packaging" / "pcpanel-gui.desktop", release / "packaging")
    shutil.copy(ROOT / "pcpanel" / "assets" / "pcpanel.svg", release / "pcpanel" / "assets")

    config = home / ".config" / "pcpanel" / "config.json"
    config.parent.mkdir(parents=True)
    config.write_text("{}\n", encoding="utf-8")
    environment = {**os.environ, "HOME": str(home), "XDG_DATA_HOME": str(data_home)}

    install = subprocess.run(
        ["bash", str(release / "install.sh")],
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )

    installed_app = home / ".local" / "opt" / "smurfpanel" / "pcpanel-gui"
    assert installed_app.is_file()
    assert (home / ".local" / "bin" / "smurfpanel").resolve() == installed_app
    assert (home / ".local" / "bin" / "smurfpanel-gui").resolve() == installed_app
    assert (home / ".local" / "bin" / "pcpanel-gui").resolve() == installed_app
    launcher = (data_home / "applications" / "smurfpanel.desktop").read_text(encoding="utf-8")
    assert f"Exec={installed_app}" in launcher
    assert "Icon=smurfpanel" in launcher
    assert f"Launch now: {home}/.local/bin/smurfpanel" in install.stdout
    assert f"Note: {home}/.local/bin is not currently in PATH." in install.stdout
    assert 'export PATH="' in install.stdout

    subprocess.run(["bash", str(release / "uninstall.sh")], env=environment, check=True)

    assert not installed_app.exists()
    assert not (data_home / "applications" / "smurfpanel.desktop").exists()
    assert config.read_text(encoding="utf-8") == "{}\n"
