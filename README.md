# PCPanel

Clean runtime for a USB controller with four dials and four buttons.

The original prototype files and USB captures are archived in `archive/`. The
new implementation is organized around the runtime path:

```text
USB reader -> report parser -> controller -> audio backend -> OSD
```

## Current Status

This is the first clean foundation:

- shared parser for the documented PCPanel report format
- controller loop separated from UI/debug code
- `pactl` audio backend as an immediate fallback
- GUI OSD overlay with one independent status bar per dial
- parser and audio-output parsing tests

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

## Build Standalone GUI

The app can be bundled with PyInstaller. This produces a self-contained app
folder for the Python/PySide6 code:

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
- `pactl` must be available on the target machine.
- The USB udev rule still needs to be installed so the app can access the device
  without root.
- Only one PCPanel process can own the USB interface at a time.

## Config

Each dial target has this shape:

```json
{
  "type": "system",
  "label": "System",
  "app_name": null,
  "binary": null,
  "stream_id": null
}
```

Target types:

- `system`: controls the default system output.
- `app`: controls an application stream. Prefer `binary` or `app_name` over
  `stream_id`, because stream IDs change when apps restart.
- `none`: ignores dial turns. Button presses still follow the saved button
  action for that dial.

Example app mapping:

```json
{
  "type": "app",
  "label": "Firefox",
  "app_name": "Firefox",
  "binary": "firefox",
  "stream_id": null
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

## Next Steps

1. Replace the fallback `pactl` backend with a persistent `pulsectl` backend.
2. Add saved/stale app targets to the GUI even when an app is not currently playing.
3. Add a systemd user service for login startup.
