# PCPanel

Clean runtime for a USB controller with four dials and four buttons.

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

Install the included udev rule once so PCPanel can access the USB device as the
signed-in desktop user:

```bash
./scripts/install_udev_rules.sh
```

Then unplug and reconnect the PCPanel. Confirm the result with:

```bash
python -m pcpanel --diagnose
```

Remove the rule if PCPanel is no longer installed:

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

After installing, launch it from your app menu as `PCPanel` or from a terminal:

```bash
pcpanel-gui
```

Update an installed copy after making code changes:

```bash
.venv/bin/python -m PyInstaller pcpanel-gui.spec --clean --noconfirm
./scripts/install_desktop.sh
```

Uninstall the user-level app:

```bash
./scripts/uninstall_desktop.sh
```

The uninstall script removes the bundled app, app-menu launcher, command
symlink, and icon. It leaves your config file in place at
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
- Install the included udev rule before normal use; do not run PCPanel as root.
- Only one PCPanel process can own the USB interface at a time.

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

## Next Steps

1. Validate the standalone bundle and udev install flow on a clean Linux system.
2. Decide whether desktop autostart is sufficient or add a systemd user service.
3. Align the visual layer with the shared Smurftech brand/devkit while retaining the current control-surface layout.
