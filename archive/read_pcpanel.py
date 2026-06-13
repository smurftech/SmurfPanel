#!/usr/bin/env python3
import errno
import sys
import usb.core
import usb.util

VENDOR_ID = 0x0483
PRODUCT_ID = 0xa3c4


def find_device():
    dev = usb.core.find(idVendor=VENDOR_ID, idProduct=PRODUCT_ID)
    if dev is None:
        raise ValueError(
            f"Device not found: idVendor=0x{VENDOR_ID:04x}, idProduct=0x{PRODUCT_ID:04x}"
        )
    return dev


def detach_kernel_driver(dev, interface):
    try:
        if dev.is_kernel_driver_active(interface):
            dev.detach_kernel_driver(interface)
            print(f"Detached kernel driver from interface {interface}")
        else:
            print(f"No kernel driver attached to interface {interface}")
    except usb.core.USBError as e:
        raise RuntimeError(f"Could not detach kernel driver from interface {interface}: {e}")


def detach_all_kernel_drivers(dev, cfg):
    printed = set()
    for interface in cfg:
        interface_number = interface.bInterfaceNumber
        if interface_number in printed:
            continue
        printed.add(interface_number)
        try:
            if dev.is_kernel_driver_active(interface_number):
                dev.detach_kernel_driver(interface_number)
                print(f"Detached kernel driver from interface {interface_number}")
            else:
                print(f"Kernel driver not active on interface {interface_number}")
        except usb.core.USBError as e:
            print(f"Warning: could not detach kernel driver from interface {interface_number}: {e}")


def claim_interface(dev, interface):
    try:
        usb.util.claim_interface(dev, interface)
        print(f"Claimed interface {interface}")
    except usb.core.USBError as e:
        if getattr(e, 'errno', None) == errno.EBUSY:
            raise RuntimeError(
                f"Could not claim interface {interface}: {e}. "
                "The device is busy or another process/driver is using it. "
                "Try running with sudo or stop the conflicting process."
            )
        if getattr(e, 'errno', None) in (errno.EACCES, errno.EPERM) or 'Access denied' in str(e):
            raise RuntimeError(
                f"Could not claim interface {interface}: permission denied. "
                "Run as root or add a udev rule for 0483:a3c4."
            )
        raise RuntimeError(f"Could not claim interface {interface}: {e}")


def release_interface(dev, interface):
    try:
        usb.util.release_interface(dev, interface)
        print(f"Released interface {interface}")
    except usb.core.USBError as e:
        print(f"Warning: could not release interface {interface}: {e}")


def list_interface_info(cfg, dev):
    printed = set()
    for interface in cfg:
        interface_number = interface.bInterfaceNumber
        if interface_number in printed:
            continue
        printed.add(interface_number)
        try:
            active = dev.is_kernel_driver_active(interface_number)
        except usb.core.USBError:
            active = None
        print(f"Interface {interface_number}: kernel driver active = {active}")
        for alt in interface:
            print(f"  Alt setting {alt.bAlternateSetting}")
            for endpoint in alt:
                direction = 'IN' if usb.util.endpoint_direction(endpoint.bEndpointAddress) == usb.util.ENDPOINT_IN else 'OUT'
                print(f"    Endpoint 0x{endpoint.bEndpointAddress:02x} {direction} max packet {endpoint.wMaxPacketSize}")


def find_in_endpoint(cfg):
    for interface in cfg:
        for alt in interface:
            for endpoint in alt:
                if usb.util.endpoint_direction(endpoint.bEndpointAddress) == usb.util.ENDPOINT_IN:
                    return endpoint, interface.bInterfaceNumber
    return None, None


def print_device_info(dev):
    print(f"Found USB device: {dev}")
    try:
        print(f"Manufacturer: {usb.util.get_string(dev, dev.iManufacturer)}")
        print(f"Product: {usb.util.get_string(dev, dev.iProduct)}")
        print(f"Serial: {usb.util.get_string(dev, dev.iSerialNumber)}")
    except usb.core.USBError:
        print("Unable to read string descriptors.")


def main():
    dev = find_device()
    print_device_info(dev)

    dev.set_configuration()
    cfg = dev.get_active_configuration()

    list_interface_info(cfg, dev)
    detach_all_kernel_drivers(dev, cfg)

    endpoint, interface_number = find_in_endpoint(cfg)
    if endpoint is None:
        raise RuntimeError("No IN endpoint found on active configuration")

    print(f"Using endpoint 0x{endpoint.bEndpointAddress:02x} on interface {interface_number}")

    print(f"Kernel driver active before claim: {dev.is_kernel_driver_active(interface_number)}")
    claim_interface(dev, interface_number)
    print(f"Kernel driver active after claim: {dev.is_kernel_driver_active(interface_number)}")

    try:
        size = endpoint.wMaxPacketSize
        print(f"Reading up to {size} bytes from endpoint 0x{endpoint.bEndpointAddress:02x}")
        data = dev.read(endpoint.bEndpointAddress, size, timeout=1000)
        print("Data read:", bytes(data))
        print("Hex:", data.tobytes().hex())
    except usb.core.USBError as e:
        if getattr(e, 'errno', None) == errno.EBUSY:
            raise RuntimeError(
                f"USB read failed: {e}. "
                "The device is busy or in use by another driver/process. "
                "Try stopping the other process or run as root."
            )
        raise RuntimeError(f"USB read failed: {e}")
    finally:
        release_interface(dev, interface_number)
        try:
            dev.attach_kernel_driver(interface_number)
        except usb.core.USBError as e:
            print(f"Warning: could not reattach kernel driver: {e}")
        usb.util.dispose_resources(dev)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
