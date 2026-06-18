import sys
import usb.core
import usb.util

VENDOR_ID = 0x0483
PRODUCT_ID = 0xA3C4
INTERFACE = 0

raw = sys.argv[1].replace(" ", "") if len(sys.argv) > 1 else "00"
payload = bytes.fromhex(raw)
if len(payload) > 64:
    raise SystemExit("Payload is longer than 64 bytes")
payload = payload + bytes(64 - len(payload))

dev = usb.core.find(idVendor=VENDOR_ID, idProduct=PRODUCT_ID)
if dev is None:
    raise SystemExit("PCPanel not found")

try:
    if dev.is_kernel_driver_active(INTERFACE):
        dev.detach_kernel_driver(INTERFACE)
except Exception:
    pass

dev.set_configuration()

try:
    # HID SET_REPORT, Output report, report ID 0
    written = dev.ctrl_transfer(0x21, 0x09, 0x0200, INTERFACE, payload, timeout=1000)
    print(f"Control SET_REPORT wrote {written} bytes: {payload.hex()}")
finally:
    try:
        dev.attach_kernel_driver(INTERFACE)
    except Exception:
        pass
    usb.util.dispose_resources(dev)
