from __future__ import annotations

import errno
import logging
import threading
from collections.abc import Callable

import usb.core
import usb.util

from pcpanel.events import ControlEvent
from pcpanel.lighting import send_output_report
from pcpanel.parser import ReportParseError, parse_report

LOGGER = logging.getLogger(__name__)

VENDOR_ID = 0x0483
PRODUCT_ID = 0xA3C4
READ_TIMEOUT_MS = 100


class PyUsbReader(threading.Thread):
    """Read one lifetime of a PCPanel USB connection."""

    def __init__(
        self,
        on_event: Callable[[ControlEvent], None],
        stop_event: threading.Event,
        vendor_id: int = VENDOR_ID,
        product_id: int = PRODUCT_ID,
        on_connected: Callable[[], None] | None = None,
        on_disconnected: Callable[[str | None], None] | None = None,
    ) -> None:
        super().__init__(daemon=True)
        self.on_event = on_event
        self.stop_event = stop_event
        self.vendor_id = vendor_id
        self.product_id = product_id
        self.on_connected = on_connected or (lambda: None)
        self.on_disconnected = on_disconnected or (lambda _message: None)
        self.last_error: str | None = None
        self._device = None
        self._interface_number: int | None = None
        self._device_lock = threading.Lock()

    def run(self) -> None:
        try:
            endpoint = self._open_endpoint()
            self.on_connected()
            while not self.stop_event.is_set():
                try:
                    with self._device_lock:
                        data = self._device.read(
                            endpoint.bEndpointAddress,
                            endpoint.wMaxPacketSize,
                            timeout=READ_TIMEOUT_MS,
                        )
                except usb.core.USBError as exc:
                    if _is_timeout_error(exc):
                        continue
                    self.last_error = f"USB read failed: {exc}"
                    LOGGER.warning(self.last_error)
                    break

                try:
                    report = bytes(data)
                    LOGGER.debug("USB report raw=%s", report.hex()[:32])
                    self.on_event(parse_report(report))
                except ReportParseError as exc:
                    LOGGER.debug("Ignoring unsupported report: %s", exc)
        except Exception as exc:
            self.last_error = str(exc)
            LOGGER.exception("USB reader stopped unexpectedly")
        finally:
            self.close()
            try:
                self.on_disconnected(self.last_error)
            except Exception:
                LOGGER.exception("USB disconnect callback failed")

    def send_output_report(self, payload: bytes) -> None:
        if self._device is None:
            raise RuntimeError("USB device is not open")
        with self._device_lock:
            send_output_report(self._device, payload)

    def close(self) -> None:
        if self._device is None or self._interface_number is None:
            return
        try:
            usb.util.release_interface(self._device, self._interface_number)
        except usb.core.USBError:
            LOGGER.debug("Unable to release USB interface", exc_info=True)
        try:
            self._device.attach_kernel_driver(self._interface_number)
        except usb.core.USBError:
            LOGGER.debug("Unable to reattach kernel driver", exc_info=True)
        usb.util.dispose_resources(self._device)
        self._device = None
        self._interface_number = None

    def _open_endpoint(self):
        device = usb.core.find(idVendor=self.vendor_id, idProduct=self.product_id)
        if device is None:
            raise RuntimeError(
                f"Device not found: {self.vendor_id:04x}:{self.product_id:04x}"
            )

        try:
            device.set_configuration()
        except usb.core.USBError as exc:
            if getattr(exc, "errno", None) != errno.EBUSY:
                raise
            LOGGER.info("USB device is busy during configuration; trying kernel-driver detach")
            _detach_kernel_drivers(device)
            try:
                device.set_configuration()
            except usb.core.USBError as retry_exc:
                if getattr(retry_exc, "errno", None) == errno.EBUSY:
                    raise RuntimeError(
                        "USB device is busy. Close any other PCPanel process, unplug/replug "
                        "the device, or check whether the kernel HID driver is still attached."
                    ) from retry_exc
                raise
        cfg = device.get_active_configuration()
        endpoint = None
        interface_number = None

        for interface in cfg:
            for alt in interface:
                for ep in _iter_endpoints(alt):
                    if usb.util.endpoint_direction(ep.bEndpointAddress) == usb.util.ENDPOINT_IN:
                        endpoint = ep
                        interface_number = interface.bInterfaceNumber
                        break
                if endpoint is not None:
                    break
            if endpoint is not None:
                break

        if endpoint is None or interface_number is None:
            raise RuntimeError("No interrupt IN endpoint found")

        _detach_kernel_driver(device, interface_number)

        try:
            usb.util.claim_interface(device, interface_number)
        except usb.core.USBError as exc:
            if getattr(exc, "errno", None) == errno.EBUSY:
                raise RuntimeError(
                    "USB interface is busy. Another process or kernel driver is using the "
                    "PCPanel device."
                ) from exc
            raise
        self._device = device
        self._interface_number = interface_number
        LOGGER.info(
            "Claimed USB interface %s using endpoint 0x%02x",
            interface_number,
            endpoint.bEndpointAddress,
        )
        return endpoint


def _is_timeout_error(exc: usb.core.USBError) -> bool:
    if getattr(exc, "errno", None) == errno.ETIMEDOUT:
        return True
    if getattr(exc, "backend_error_code", None) == -7:
        return True
    return "timed out" in str(exc).lower()


def _detach_kernel_drivers(device) -> None:
    for cfg in device:
        for interface in cfg:
            _detach_kernel_driver(device, interface.bInterfaceNumber)


def _detach_kernel_driver(device, interface_number: int) -> None:
    try:
        if device.is_kernel_driver_active(interface_number):
            device.detach_kernel_driver(interface_number)
            LOGGER.info("Detached kernel driver from USB interface %s", interface_number)
    except NotImplementedError:
        LOGGER.debug("Kernel driver checks are not supported by this platform")
    except usb.core.USBError:
        LOGGER.debug("Kernel driver detach failed for interface %s", interface_number, exc_info=True)


def _iter_endpoints(alt):
    if hasattr(alt, "bEndpointAddress"):
        yield alt
    else:
        yield from alt
