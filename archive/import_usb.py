import usb.core
import usb.util
import sys

# 1. Find the device (Replace IDs with your device's hex values)
VENDOR_ID = 0x0483
PRODUCT_ID = 0xa3c4

device = usb.core.find(idVendor=VENDOR_ID, idProduct=PRODUCT_ID)

if device is None:
    raise ValueError("Device not found. Check your IDs and connection.")

# 2. Handle kernel drivers
# If Linux has already loaded a driver (like a HID driver), you must detach it.
if device.is_kernel_driver_active(0):
    try:
        device.detach_kernel_driver(0)
        print("Kernel driver detached")
    except usb.core.USBError as e:
        sys.exit(f"Could not detach kernel driver: {str(e)}")

# 3. Set the active configuration
# Most devices have only one configuration (index 0)
device.set_configuration()

# 4. Access the interface and endpoints
# This step depends on your specific device's structure
cfg = device.get_active_configuration()
intf = cfg[(0,0)]

# Find the first OUT endpoint (to send data)
ep_out = usb.util.find_descriptor(
    intf,
    custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_OUT
)

# 5. Send data
data = "Hello USB"
ep_out.write(data)
print("Data sent successfully")
