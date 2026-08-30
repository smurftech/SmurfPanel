# SmurfPanel

Smurftech device-control application for PCPanel Mini hardware with four dials
and four buttons.

The original prototype files and USB captures are archived in `archive/`. The
new implementation is organized around the runtime path:

```text
USB reader -> report parser -> controller -> audio backend -> OSD
```

## Current Status

The runtime now includes:

- shared parser for the documented PCPanel report format
- controller loop separated from UI/debug code
- persistent `pulsectl` backend for normal PulseAudio / PipeWire-Pulse control
- `pactl` subprocess backend retained as a diagnostic/fallback implementation
- application targets resolved by stable application ID/binary/name metadata and applied to all matching active streams
- automatic USB reconnect with bounded backoff after device loss or failed opens
- GUI device status driven by the real USB connection lifecycle
- GUI OSD overlay with one independent status bar per dial
- parser, audio, USB reconnect, config and controller tests

## Run

```bash
python -m pcpanel
```

Run the GUI:

```bash
python -m pcpanel.gui
```

The GUI starts the same controller path as the CLI, shows live dial movement,
shows mute state, edits the config file, and can enable launch-on-login from
the bottom control bar.

Each channel shows whether its target is active, waiting for an application,
using the system output, or unassigned. Configuration changes remain explicit:
use `Save config` to persist them or `Revert` to restore the last saved file.
Quitting with pending changes offers Save, Discard, and Cancel choices.

GUI shortcuts:

- `Ctrl+S`: save configuration
- `Ctrl+Shift+R`: revert unsaved configuration changes
- `F5`: refresh applications and output devices

The bottom control bar also includes an `About` popup with app version,
creator, website, device, backend, config, and startup-path details.

The default config is loaded from:

```text
~/.config/pcpanel/config.json
```

If the file does not exist, dial 1 controls the system volume and the other
dials are unassigned.

Create the default config:

```bash
python -m pcpanel --init-config
```

Print the default config without writing it:

```bash
python -m pcpanel --print-default-config
```

Run with a config file in the repo while testing:

```bash
python -m pcpanel -v --config config.example.json
```

Run the GUI with a specific config:

```bash
python -m pcpanel.gui -v --config config.example.json
```

List active application streams:

```bash
python -m pcpanel --list-streams
```

Check system readiness and USB detection:

```bash
python -m pcpanel --diagnose
```

## USB Permissions

Install the included udev rule once so SmurfPanel can access the USB device as the
signed-in desktop user:

```bash
./scripts/install_udev_rules.sh
```

Then unplug and reconnect the PCPanel Mini. Confirm the result with:

```bash
python -m pcpanel --diagnose
```

Remove the rule if SmurfPanel is no longer installed:

```bash
./scripts/uninstall_udev_rules.sh
```

The rule matches only the supported PCPanel Mini USB identifier `0483:a3c4`
and grants access through the desktop session's `uaccess` policy.

## Build Standalone GUI

The app can be bundled with PyInstaller. This produces a self-contained app
folder for the Python/PySide6 code. Linux builds also require `objdump`,
normally provided by the distribution's `binutils` package:

```bash
python -m PyInstaller pcpanel-gui.spec --clean --noconfirm
```

The bundled executable is:

```text
dist/pcpanel-gui/pcpanel-gui
```

Run it with:

```bash
./dist/pcpanel-gui/pcpanel-gui
```

Install it into your user application menu:

```bash
./scripts/install_desktop.sh
```

To create a portable archive that can be installed without the source tree or
a Python environment:

```bash
./scripts/validate_release.sh --build
bash ./scripts/package_release.sh
```

This creates a versioned archive and checksum under `dist/`, for example:

```text
dist/SmurfPanel-0.1.0-linux-x86_64.tar.gz
dist/SmurfPanel-0.1.0-linux-x86_64.tar.gz.sha256
```

On the destination computer, verify, extract, and install it for the current
user:

```bash
sha256sum -c SmurfPanel-0.1.0-linux-x86_64.tar.gz.sha256
tar -xzf SmurfPanel-0.1.0-linux-x86_64.tar.gz
cd SmurfPanel-0.1.0-linux-x86_64
./install.sh
```

Commands are installed under `~/.local/bin`. If that directory is not in the
current shell `PATH`, the installer prints both a direct launch path and the
exact `export PATH=...` line needed for the current terminal or shell profile.
It does not modify shell configuration files automatically.

Use `./install.sh --with-udev` to install the narrowly scoped PCPanel Mini USB
permission rule at the same time. This option uses `sudo`; the normal user app
installation does not.

After installing, launch it from your app menu as `SmurfPanel` or from a terminal:

```bash
smurfpanel
```

Editable/package installs also provide the branded `smurfpanel` and
`smurfpanel-gui` command aliases. The existing `pcpanel` commands and config
path remain supported for compatibility.

Update an installed copy after making code changes:

```bash
.venv/bin/python -m PyInstaller pcpanel-gui.spec --clean --noconfirm
./scripts/install_desktop.sh
```

Uninstall the user-level app:

```bash
./scripts/uninstall_desktop.sh
```

From a portable release directory, use `./uninstall.sh`. Add `--remove-udev`
to also remove the optional USB permission rule.

The uninstall script removes the bundled app, app-menu launcher, branded and
legacy command symlinks, and icon. It leaves your config file in place at
`~/.config/pcpanel/config.json`.

The GUI's `Open on startup` checkbox writes a user autostart launcher at:

```text
~/.config/autostart/pcpanel-gui.desktop
```

Notes:

- The bundle is still platform-specific. Build it on the Linux distribution you
  plan to run it on.
- The normal runtime talks to the PulseAudio-compatible server through
  `pulsectl`; this works with PipeWire-Pulse as used by current Linux desktops.
- `pactl` remains useful for diagnostics and the fallback backend.
- Install the included udev rule before normal use; do not run SmurfPanel as root.
- Only one SmurfPanel process can own the PCPanel Mini USB interface at a time.

## Config

Each dial target has this shape:

```json
{
  "type": "system",
  "label": "System",
  "app_name": null,
  "app_id": null,
  "binary": null
}
```

Target types:

- `system`: controls the default system output.
- `app`: controls an application using the stable `app_id` when available,
  with `binary` and `app_name` fallbacks. Volatile stream IDs are not persisted.
  When an application has multiple active audio streams, all matching streams
  are controlled together.
- `none`: ignores dial turns. Button presses still follow the saved button
  action for that dial.

Example app mapping:

```json
{
  "type": "app",
  "label": "Firefox",
  "app_name": "Firefox",
  "app_id": "org.mozilla.firefox",
  "binary": "firefox"
}
```

Button press actions are stored separately from dial volume targets in
`button_actions`. Each dial defaults to the original mute/unmute behavior:

```json
{
  "type": "mute",
  "output_name": null,
  "output_label": null,
  "toggle_output_name": null,
  "toggle_output_label": null
}
```

Button action types:

- `mute`: toggles mute for that dial's volume target.
- `set_output`: switches to `output_name`.
- `toggle_output`: switches between `output_name` and `toggle_output_name`.

The GUI lists available output devices and saves the selected device names in
the config so the actions are active again on the next launch.

## Release Validation

Run the repeatable validation flow before promoting a release:

```bash
./scripts/validate_release.sh --build
```

This runs the automated suite, validates the example configuration, compiles
the package, builds a wheel, and optionally creates the standalone GUI bundle.
The hardware, desktop lifecycle, and clean-system checks are documented in
`RELEASE_CHECKLIST.md`.

## Automated GitHub Releases

The `Build SmurfPanel release` GitHub Actions workflow builds the Linux x86_64
bundle on Ubuntu 22.04. Pull requests to `dev` and manual runs build and upload
an artifact without publishing a GitHub Release. Version tags additionally
publish the validated archive and checksum.

For a release:

1. Update `project.version` in `pyproject.toml` and merge the change through
   `dev` to `main`.
2. Run the workflow manually from `main` and test its downloaded artifact.
3. Tag that exact validated `main` commit:

```bash
git switch main
git pull --ff-only origin main
git tag -a v0.1.0 -m "SmurfPanel v0.1.0"
git push origin v0.1.0
```

The tag must exactly match the package version. A mismatch stops the workflow
before building or publishing. If a job fails transiently, rerun it from the
Actions page. If code must change, fix it through the normal branch flow and
use a new patch version; do not move a tag that has already been published.

## Next Steps

1. Validate the portable archive and udev install flow on a clean Linux system.
2. Decide whether desktop autostart is sufficient or add a systemd user service.
3. Add additional platform-native packages only after the portable archive is
   proven across the supported Linux distributions.
