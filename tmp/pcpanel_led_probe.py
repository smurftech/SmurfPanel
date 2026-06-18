
import sys
import usb.core
import usb.util

VENDOR_ID = 0x0483
PRODUCT_ID = 0xA3C4
INTERFACE = 0
ENDPOINT_OUT = 0x01

if len(sys.argv) != 2:
    print("Usage: sudo python /tmp/pcpanel_led_probe.py <hex-bytes>")
    print("Example: sudo python /tmp/pcpanel_led_probe.py 000000")
    sys.exit(2)

raw = sys.argv[1].replace(" ", "")
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
except (NotImplementedError, usb.core.USBError):
    pass

dev.set_configuration()
usb.util.claim_interface(dev, INTERFACE)

try:
    written = dev.write(ENDPOINT_OUT, payload, timeout=1000)
    print(f"Wrote {written} bytes: {payload.hex()}")
finally:
    usb.util.release_interface(dev, INTERFACE)
    try:
        dev.attach_kernel_driver(INTERFACE)
    except usb.core.USBError:
        pass
    usb.util.dispose_resources(dev)