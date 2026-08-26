from __future__ import annotations

import shlex
import sys
from pathlib import Path

AUTOSTART_FILENAME = "pcpanel-gui.desktop"
APP_NAME = "PCPanel"


def autostart_path() -> Path:
    return Path.home() / ".config" / "autostart" / AUTOSTART_FILENAME


def is_autostart_enabled(path: Path | None = None) -> bool:
    startup_path = path or autostart_path()
    if not startup_path.exists():
        return False
    try:
        content = startup_path.read_text(encoding="utf-8")
    except OSError:
        return False
    return "Hidden=true" not in content


def set_autostart_enabled(
    enabled: bool,
    path: Path | None = None,
    command: list[str] | None = None,
) -> None:
    startup_path = path or autostart_path()
    if not enabled:
        startup_path.unlink(missing_ok=True)
        return
    startup_path.parent.mkdir(parents=True, exist_ok=True)
    launch_command = command or default_launch_command()
    startup_path.write_text(_desktop_entry(launch_command), encoding="utf-8")
    startup_path.chmod(0o755)


def default_launch_command() -> list[str]:
    current_executable = Path(sys.executable)
    if getattr(sys, "frozen", False):
        return [str(current_executable)]

    installed_command = Path.home() / ".local" / "bin" / "pcpanel-gui"
    if installed_command.exists():
        return [str(installed_command)]

    installed_app = Path.home() / ".local" / "opt" / "pcpanel-gui" / "pcpanel-gui"
    if installed_app.exists():
        return [str(installed_app)]

    return [str(current_executable), "-m", "pcpanel.gui"]


def _desktop_entry(command: list[str]) -> str:
    return (
        "[Desktop Entry]\n"
        "Type=Application\n"
        f"Name={APP_NAME}\n"
        "Comment=USB audio control surface\n"
        f"Exec={shlex.join(command)}\n"
        "Icon=pcpanel\n"
        "Terminal=false\n"
        "X-GNOME-Autostart-enabled=true\n"
    )
