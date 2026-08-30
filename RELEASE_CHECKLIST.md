# SmurfPanel Release Checklist

## Automated validation

- [ ] Install the Linux `binutils` package so `objdump` is available.
- [ ] Run `./scripts/validate_release.sh --build`.
- [ ] Confirm the test suite, configuration validation, wheel build, and PyInstaller build pass.
- [ ] Run `bash ./scripts/package_release.sh` and verify the generated checksum.
- [ ] Extract the release archive outside the repository and install with `./install.sh`.
- [ ] Run `./dist/pcpanel-gui/pcpanel-gui --config config.example.json`.
- [ ] Launch the installed copy from the application menu.
- [ ] Confirm `smurfpanel`, `smurfpanel-gui`, and legacy `pcpanel-gui` resolve from `~/.local/bin` in a new terminal.

## Clean-system and permissions validation

- [ ] Install the udev rule with `./scripts/install_udev_rules.sh`.
- [ ] Unplug and reconnect the PCPanel Mini.
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
- [ ] Run `./uninstall.sh` and confirm the app, launcher, icon, and command links are removed.
- [ ] Confirm uninstall preserves `~/.config/pcpanel/config.json`.

## Release handoff

- [ ] Update `project.version` in `pyproject.toml` and release notes.
- [ ] Merge the milestone branch into `dev`, then promote the validated `dev` branch to `main`.
- [ ] Run `Build SmurfPanel release` manually from `main` and test its downloaded artifact.
- [ ] Create an annotated `vMAJOR.MINOR.PATCH` tag on that exact `main` commit.
- [ ] Confirm the tag workflow publishes both the Linux archive and checksum.
- [ ] Download the published files, verify the checksum, install, launch, and uninstall once.
