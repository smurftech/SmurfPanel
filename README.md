# PcPanel USB Reader

A small Python utility for reading from the STMicroelectronics PCPanel Mini device.

## Requirements

This project includes Arch Linux package names in `requirements.txt`.

### Install dependencies on Arch Linux

```bash
sudo pacman -S python-pyusb python-requests python-urllib3 python-numpy python-pandas python-yaml python-dotenv python-click python-flask python-fastapi python-uvicorn python-jinja python-sqlalchemy python-alembic python-pydantic python-pytest python-pytest-cov python-black python-mypy python-dateutil python-cryptography python-six python-packaging python-gunicorn python-psycopg2
```

> The `requirements.txt` file also includes the same package names.

## Usage

Run the USB reader script with Python 3:

```bash
python3 read_pcpanel.py
```

### Run the webview interface

Use the helper script to create and activate a virtual environment:

```bash
cd /home/smurftech/GIT_REPOS/PcPanel
source ./setup_env.sh
```

This creates `.venv`, installs dependencies, and activates the environment.

If you prefer manual installation instead, install the webview dependency and run:

```bash
pip install pywebview
python3 web_pcpanel.py
```

If the default backend is not available, install either GTK or Qt support:

```bash
pip install pywebview[gtk] PyGObject
# or
pip install pywebview[qt] qtpy PySide6
```

If you get `ImportError: No module named 'qtpy'`, make sure you are running inside the activated `.venv` created by `source ./setup_env.sh`.

If you are running on Wayland, Qt is usually more reliable than GTK for `pywebview`, so prefer the Qt backend when possible.

This opens a local HTML-based interface backed by the same USB/pactl logic.

If the script cannot find the device, make sure the USB device is connected and that you have permission to access it.

## Notes

- The script uses `pyusb` to communicate with the USB device.
- Depending on the device, you may need to run the script with `sudo` or update your udev rules to allow non-root USB access.
- This repository currently contains only a basic example script for the specified `0483:a3c4` STMicroelectronics device.

## udev rule (allow non-root access)

A udev rule is included in `99-pcpanel.rules` to allow members of the `uucp` group to access the device without `sudo`.

Install it system-wide with:

```bash
sudo cp 99-pcpanel.rules /etc/udev/rules.d/99-pcpanel.rules
sudo udevadm control --reload
sudo udevadm trigger
```

Then add your user to the `uucp` group (log out/in afterwards):

```bash
sudo usermod -aG uucp $USER
```

If you prefer a more permissive rule, open `99-pcpanel.rules` and change `MODE="0660"` to `MODE="0666"`.

