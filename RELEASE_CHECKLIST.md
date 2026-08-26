# PCPanel Release Checklist

## Automated validation

- [ ] Install the Linux `binutils` package so `objdump` is available.
- [ ] Run `./scripts/validate_release.sh --build`.
- [ ] Confirm the test suite, configuration validation, wheel build, and PyInstaller build pass.
- [ ] Run `./dist/pcpanel-gui/pcpanel-gui --config config.example.json`.
- [ ] Install with `./scripts/install_desktop.sh` and launch from the application menu.
- [ ] Confirm `pcpanel-gui` resolves from `~/.local/bin` in a new terminal.

## Clean-system and permissions validation

- [ ] Install the udev rule with `./scripts/install_udev_rules.sh`.
- [ ] Unplug and reconnect the PCPanel.
- [ ] Run `pcpanel --diagnose` and confirm every check passes.
- [ ] Confirm the app connects without root privileges.
- [ ] Confirm a missing rule produces an actionable permission message.

## Hardware validation

- [ ] Verify all four dials, buttons, mute actions, output switching, LEDs, and OSD.
- [ ] Verify all matching streams for one application move together.
- [ ] Unplug for at least 10 seconds, reconnect, and retest controls and LEDs.
- [ ] Start the app disconnected, then connect and retest controls.
- [ ] Suspend and resume the computer, then retest controls and LEDs.

## Desktop lifecycle

- [ ] Enable launch-on-login, sign out/in, and confirm the app starts.
- [ ] Disable launch-on-login and confirm the autostart entry is removed.
- [ ] Run `./scripts/uninstall_desktop.sh` and confirm the app/launcher are removed.
- [ ] Confirm uninstall preserves `~/.config/pcpanel/config.json`.

## Release handoff

- [ ] Update version and release notes when assigning a release tag.
- [ ] Merge the milestone branch into `dev`, then promote the validated `dev` branch to `main`.
- [ ] Tag the validated `main` commit and attach the Linux bundle or archive.
