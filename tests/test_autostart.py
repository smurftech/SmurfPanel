from pcpanel.autostart import is_autostart_enabled, set_autostart_enabled


def test_set_autostart_enabled_writes_desktop_entry(tmp_path) -> None:
    path = tmp_path / "pcpanel-gui.desktop"

    set_autostart_enabled(True, path=path, command=["/opt/pcpanel/pcpanel-gui"])

    content = path.read_text(encoding="utf-8")
    assert "Type=Application" in content
    assert "Name=PCPanel" in content
    assert "Exec=/opt/pcpanel/pcpanel-gui" in content
    assert is_autostart_enabled(path) is True


def test_set_autostart_disabled_removes_desktop_entry(tmp_path) -> None:
    path = tmp_path / "pcpanel-gui.desktop"
    set_autostart_enabled(True, path=path, command=["/opt/pcpanel/pcpanel-gui"])

    set_autostart_enabled(False, path=path)

    assert path.exists() is False
    assert is_autostart_enabled(path) is False


def test_hidden_autostart_entry_is_not_enabled(tmp_path) -> None:
    path = tmp_path / "pcpanel-gui.desktop"
    path.write_text("[Desktop Entry]\nHidden=true\n", encoding="utf-8")

    assert is_autostart_enabled(path) is False
