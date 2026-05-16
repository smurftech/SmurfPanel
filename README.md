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

If the script cannot find the device, make sure the USB device is connected and that you have permission to access it.

## Notes

- The script uses `pyusb` to communicate with the USB device.
- Depending on the device, you may need to run the script with `sudo` or update your udev rules to allow non-root USB access.
- This repository currently contains only a basic example script for the specified `0483:a3c4` STMicroelectronics device.

## udev rule (allow non-root access)

A udev rule is included in `99-pcpanel.rules` to allow members of the `plugdev` group to access the device without `sudo`.

Install it system-wide with:

```bash
sudo cp 99-pcpanel.rules /etc/udev/rules.d/99-pcpanel.rules
sudo udevadm control --reload
sudo udevadm trigger
```

Then add your user to the `plugdev` group (log out/in afterwards):

```bash
sudo usermod -aG plugdev $USER
```

If you prefer a more permissive rule, open `99-pcpanel.rules` and change `MODE="0660"` to `MODE="0666"`.

