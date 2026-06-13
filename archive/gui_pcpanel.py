#!/usr/bin/env python3
"""
Simple Tkinter GUI for the PCPanel Mini (0483:a3c4).
- Starts a background thread that reads interrupt IN reports from the device.
- Shows raw hex of the latest report and attempts a simple decode:
  - byte0: button bitmask (low 4 bits = buttons 1-4)
  - bytes 1..4: analog values (0-255) for 4 dials if present

Adjust parsing in `parse_report` if your device uses a different report layout.
"""

import json
import os
import sys
import threading
import queue
import time
import subprocess
import re
import usb.core
import usb.util
import errno
import tkinter as tk
from tkinter import ttk, filedialog

VENDOR_ID = 0x0483
PRODUCT_ID = 0xa3c4
READ_TIMEOUT = 500  # ms
CONFIG_FILE = os.path.expanduser('~/.config/pcpanel_gui/mappings.json')


def find_device():
    dev = usb.core.find(idVendor=VENDOR_ID, idProduct=PRODUCT_ID)
    if dev is None:
        raise RuntimeError("Device not found")
    return dev


def prepare_device(dev):
    dev.set_configuration()
    cfg = dev.get_active_configuration()
    # find an IN endpoint (robust to alt being an Endpoint or an altsetting)
    endpoint = None
    intf_num = None
    for interface in cfg:
        for alt in interface:
            # alt might be an Endpoint instance on some platforms
            if hasattr(alt, 'bEndpointAddress'):
                ep = alt
                if usb.util.endpoint_direction(ep.bEndpointAddress) == usb.util.ENDPOINT_IN:
                    endpoint = ep
                    intf_num = interface.bInterfaceNumber
                    break
            else:
                for ep in alt:
                    if usb.util.endpoint_direction(ep.bEndpointAddress) == usb.util.ENDPOINT_IN:
                        endpoint = ep
                        intf_num = interface.bInterfaceNumber
                        break
            if endpoint:
                break
        if endpoint:
            break
    if endpoint is None:
        raise RuntimeError("No IN endpoint found")

    # try to detach kernel driver if necessary
    try:
        if dev.is_kernel_driver_active(intf_num):
            dev.detach_kernel_driver(intf_num)
    except Exception:
        pass

    usb.util.claim_interface(dev, intf_num)
    return dev, endpoint, intf_num


def release_device(dev, intf_num):
    try:
        usb.util.release_interface(dev, intf_num)
    except Exception:
        pass
    try:
        dev.attach_kernel_driver(intf_num)
    except Exception:
        pass
    try:
        usb.util.dispose_resources(dev)
    except Exception:
        pass


# Basic parser: adapt as needed for your device report format
def parse_report(data_bytes):
    # return dict with raw hex and decoded fields
    raw_hex = data_bytes.hex()
    parsed = {
        "raw": raw_hex,
        "first6": raw_hex[:6],
        "event_type": None,
        "event_target": None,
        "event_value": None,
        "buttons": [],
        "analogs": [],
    }
    if len(raw_hex) >= 6:
        first6 = raw_hex[:6]
        parsed["first6"] = first6
        event_type = None
        event_target = None
        event_value = None
        try:
            kind = first6[1]
            target_hex = first6[3]
            value_hex = first6[4:6]
            if kind == '1':
                event_type = 'dial'
                event_target = f"Dial {int(target_hex, 16) + 1}"
                event_value = int(value_hex, 16)
                parsed["analogs"] = [0, 0, 0, 0]
                if 0 <= int(target_hex, 16) < 4:
                    parsed["analogs"][int(target_hex, 16)] = event_value
            elif kind == '2':
                event_type = 'button'
                button_num = int(target_hex, 16) + 1
                event_target = f"Button {button_num}"
                event_value = int(value_hex, 16)
                parsed["buttons"] = [0, 0, 0, 0]
                if 0 <= int(target_hex, 16) < 4:
                    parsed["buttons"][int(target_hex, 16)] = 1 if event_value != 0 else 0
        except Exception:
            event_type = None
            event_target = None
            event_value = None
        parsed["event_type"] = event_type
        parsed["event_target"] = event_target
        parsed["event_value"] = event_value
    else:
        parsed["first6"] = raw_hex[:6]
    # fallback generic decode for full report if no event detected
    if not parsed["buttons"] and len(data_bytes) >= 1:
        b0 = data_bytes[0]
        buttons = [(b0 >> i) & 1 for i in range(4)]
        parsed["buttons"] = buttons
    if not parsed["analogs"] and len(data_bytes) >= 5:
        parsed["analogs"] = [int(data_bytes[i]) for i in range(1, 5)]
    elif not parsed["analogs"] and len(data_bytes) >= 3:
        try:
            import struct

            if len(data_bytes) >= 5:
                a = struct.unpack_from('<4B', data_bytes, 1)
                parsed["analogs"] = list(a)
        except Exception:
            pass
    return parsed


class USBReaderThread(threading.Thread):
    def __init__(self, out_q, stop_event):
        super().__init__(daemon=True)
        self.out_q = out_q
        self.stop_event = stop_event
        self.dev = None
        self.endpoint = None
        self.intf = None

    def run(self):
        try:
            self.dev = find_device()
            # try to set configuration; if it's busy, attempt to detach kernel drivers
            try:
                self.dev.set_configuration()
            except usb.core.USBError as e:
                if getattr(e, 'errno', None) == errno.EBUSY:
                    # attempt to detach kernel drivers from all interfaces across configs
                    try:
                        for cfg in self.dev:
                            for interface in cfg:
                                intf_num = interface.bInterfaceNumber
                                try:
                                    if self.dev.is_kernel_driver_active(intf_num):
                                        self.dev.detach_kernel_driver(intf_num)
                                        self.out_q.put({"info": f"Detached kernel driver from interface {intf_num}"})
                                except Exception as de:
                                    self.out_q.put({"warning": f"Could not detach kernel driver {intf_num}: {de}"})
                    except Exception:
                        pass
                    # retry set_configuration
                    try:
                        self.dev.set_configuration()
                    except Exception as e2:
                        self.out_q.put({"error": f"set_configuration failed after detach: {e2}"})
                        return
                elif getattr(e, 'errno', None) in (errno.EACCES, errno.EPERM) or 'Access denied' in str(e):
                    self.out_q.put({"error": "Permission denied accessing USB device. Run as root or add a udev rule for 0483:a3c4."})
                    return
                else:
                    self.out_q.put({"error": f"set_configuration failed: {e}"})
                    return
            cfg = self.dev.get_active_configuration()
            # locate endpoint and interface
            for interface in cfg:
                for alt in interface:
                    if hasattr(alt, 'bEndpointAddress'):
                        ep = alt
                        if usb.util.endpoint_direction(ep.bEndpointAddress) == usb.util.ENDPOINT_IN:
                            self.endpoint = ep
                            self.intf = interface.bInterfaceNumber
                            break
                    else:
                        for ep in alt:
                            if usb.util.endpoint_direction(ep.bEndpointAddress) == usb.util.ENDPOINT_IN:
                                self.endpoint = ep
                                self.intf = interface.bInterfaceNumber
                                break
                    if self.endpoint:
                        break
                if self.endpoint:
                    break
            if self.endpoint is None:
                self.out_q.put({"error": "No IN endpoint found"})
                return

            try:
                if self.dev.is_kernel_driver_active(self.intf):
                    try:
                        self.dev.detach_kernel_driver(self.intf)
                        self.out_q.put({"info": f"Detached kernel driver from interface {self.intf}"})
                    except usb.core.USBError as e:
                        self.out_q.put({"warning": f"Could not detach kernel driver: {e}"})
                usb.util.claim_interface(self.dev, self.intf)
            except Exception as e:
                self.out_q.put({"error": f"Claim failed: {e}"})
                return

            max_packet = self.endpoint.wMaxPacketSize
            while not self.stop_event.is_set():
                try:
                    data = self.dev.read(self.endpoint.bEndpointAddress, max_packet, timeout=READ_TIMEOUT)
                    parsed = parse_report(bytes(data))
                    self.out_q.put(parsed)
                except usb.core.USBError as e:
                    # timeout is normal
                    if getattr(e, 'errno', None) in (errno.ETIMEDOUT, None):
                        # continue on timeout
                        continue
                    if getattr(e, 'errno', None) == errno.EBUSY:
                        self.out_q.put({"error": "Resource busy (EBUSY)"})
                        break
                    if getattr(e, 'errno', None) in (errno.EACCES, errno.EPERM) or 'Access denied' in str(e):
                        self.out_q.put({"error": "Permission denied accessing USB device. Run as root or add a udev rule for 0483:a3c4."})
                        break
                    # other errors: report then break
                    self.out_q.put({"error": f"USB error: {e}"})
                    break
                except Exception as e:
                    self.out_q.put({"error": f"Reader exception: {e}"})
                    break
        finally:
            if self.dev and self.intf is not None:
                try:
                    release_device(self.dev, self.intf)
                except Exception:
                    pass


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("PCPanel Monitor")
        self.geometry("520x360")
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        self.out_q = queue.Queue()
        self.stop_event = threading.Event()
        self.reader = None
        self.log = []  # list of (timestamp, raw, buttons, analogs)
        # track previous states to detect changes/edge transitions
        self.prev_buttons = [0, 0, 0, 0]
        self.prev_analogs = [0, 0, 0, 0]
        # per-dial mapping: -1 = system, None = no mapping, int = sink-input index
        self.dial_sink_map = [-1, None, None, None]
        # map display string -> sink-input index
        self.sink_input_map = {}
        self.saved_dial_targets = self.load_saved_dial_targets()

        # Controls
        ctrl_frame = ttk.Frame(self)
        ctrl_frame.pack(fill='x', padx=8, pady=8)
        self.start_btn = ttk.Button(ctrl_frame, text="Start", command=self.start)
        self.start_btn.pack(side='left')
        self.stop_btn = ttk.Button(ctrl_frame, text="Stop", command=self.stop, state='disabled')
        self.stop_btn.pack(side='left', padx=6)
        self.save_btn = ttk.Button(ctrl_frame, text="Save Log", command=self.save_log)
        self.save_btn.pack(side='left', padx=6)

        # Raw output
        raw_frame = ttk.LabelFrame(self, text="Raw Report")
        raw_frame.pack(fill='x', padx=8, pady=4)
        self.raw_var = tk.StringVar(value="-")
        ttk.Label(raw_frame, textvariable=self.raw_var).pack(anchor='w', padx=6, pady=6)
        self.first6_var = tk.StringVar(value="-")
        ttk.Label(raw_frame, text="First 6 chars:").pack(anchor='w', padx=6)
        ttk.Label(raw_frame, textvariable=self.first6_var).pack(anchor='w', padx=6, pady=(0, 6))
        self.event_var = tk.StringVar(value="-")
        ttk.Label(raw_frame, text="Decoded event:").pack(anchor='w', padx=6)
        ttk.Label(raw_frame, textvariable=self.event_var).pack(anchor='w', padx=6, pady=(0, 6))

        # Buttons
        btn_frame = ttk.LabelFrame(self, text="Buttons")
        btn_frame.pack(fill='x', padx=8, pady=4)
        self.button_vars = [tk.StringVar(value='OFF') for _ in range(4)]
        for i in range(4):
            ttk.Label(btn_frame, text=f"Button {i+1}").grid(row=0, column=i, padx=6)
            ttk.Label(btn_frame, textvariable=self.button_vars[i], width=6).grid(row=1, column=i, padx=6)

        # Analogs
        analog_frame = ttk.LabelFrame(self, text="Analogs")
        analog_frame.pack(fill='x', padx=8, pady=4)
        self.analog_vars = [tk.IntVar(value=0) for _ in range(4)]
        for i in range(4):
            ttk.Label(analog_frame, text=f"Dial {i+1}").grid(row=0, column=i, padx=6)
            ttk.Progressbar(analog_frame, orient='vertical', length=120, maximum=255, variable=self.analog_vars[i]).grid(row=1, column=i, padx=6)
            ttk.Label(analog_frame, textvariable=self.analog_vars[i]).grid(row=2, column=i, padx=6)

        # Application mapping for dials 1..4
        sink_map_frame = ttk.LabelFrame(self, text="Per-Dial Target")
        sink_map_frame.pack(fill='x', padx=8, pady=4)
        values = self.saved_dial_targets
        if len(values) != 4:
            values = ['System', 'None', 'None', 'None']
        self.app_combobox_vars = [tk.StringVar(value=values[i]) for i in range(4)]
        self.app_comboboxes = [None, None, None, None]
        for i in range(4):
            ttk.Label(sink_map_frame, text=f"Dial {i+1} target").grid(row=0, column=i, padx=6)
            cb = ttk.Combobox(sink_map_frame, textvariable=self.app_combobox_vars[i], state='readonly', width=24)
            cb['values'] = ['System', 'None']
            cb.grid(row=1, column=i, padx=6)
            # bind with a lambda capturing index
            cb.bind('<<ComboboxSelected>>', lambda e, idx=i: self.on_app_selected(idx, e))
            self.app_comboboxes[i] = cb

        # start periodic refresh of sink-inputs
        self.after(1500, self.refresh_sink_inputs)

        # Status
        self.status_var = tk.StringVar(value='Idle')
        ttk.Label(self, textvariable=self.status_var).pack(fill='x', padx=8, pady=6)

        # schedule UI update
        self.after(100, self._poll_queue)

    def start(self):
        if self.reader and self.reader.is_alive():
            return
        self.stop_event.clear()
        self.reader = USBReaderThread(self.out_q, self.stop_event)
        self.reader.start()
        self.start_btn.config(state='disabled')
        self.stop_btn.config(state='normal')
        self.status_var.set('Running')

    def stop(self):
        self.stop_event.set()
        self.start_btn.config(state='normal')
        self.stop_btn.config(state='disabled')
        self.status_var.set('Stopping')

    def _poll_queue(self):
        try:
            while True:
                item = self.out_q.get_nowait()
                if 'error' in item:
                    self.status_var.set(f"Error: {item['error']}")
                if 'warning' in item:
                    self.status_var.set(f"Warning: {item['warning']}")
                if 'info' in item:
                    self.status_var.set(item['info'])
                raw = item.get('raw')
                if raw:
                    self.raw_var.set(raw)
                    self.first6_var.set(item.get('first6', '-'))
                    event_type = item.get('event_type')
                    event_target = item.get('event_target')
                    event_value = item.get('event_value')
                    if event_type:
                        self.event_var.set(f"{event_type} {event_target} = {event_value}")
                    else:
                        self.event_var.set('-')
                    if event_type == 'dial' and event_target and 'Dial' in event_target:
                        try:
                            m = re.search(r'Dial\s*(\d+)', event_target)
                            if m:
                                dial_num = int(m.group(1))
                                if 1 <= dial_num <= 4:
                                    val = int(event_value) if event_value is not None else None
                                    if val is not None:
                                        percent = int(val * 100 / 255)
                                        if percent != self.prev_analogs[dial_num-1]:
                                            sink_idx = self.dial_sink_map[dial_num-1]
                                            if sink_idx == -1:
                                                try:
                                                    subprocess.run(['pactl', 'set-sink-volume', '@DEFAULT_SINK@', f'{percent}%'], check=True, timeout=1)
                                                    self.status_var.set(f'Dial {dial_num} -> System {percent}%')
                                                except Exception as e:
                                                    self.status_var.set(f'Error setting system volume: {e}')
                                            elif sink_idx is not None:
                                                try:
                                                    subprocess.run(['pactl', 'set-sink-input-volume', str(sink_idx), f'{percent}%'], check=True, timeout=1)
                                                    self.status_var.set(f'Dial {dial_num} -> App {percent}%')
                                                except Exception as e:
                                                    self.status_var.set(f'Error setting app volume: {e}')
                                            self.prev_analogs[dial_num-1] = percent
                        except Exception:
                            pass
                    # append to log with timestamp
                    ts = time.time()
                    self.log.append((ts, item))
                buttons = item.get('buttons')
                if buttons is not None:
                    # Only treat toggle actions when the event is a real button event
                    is_button_event = (event_type == 'button')
                    for i, val in enumerate(buttons):
                        if is_button_event:
                            prev = self.prev_buttons[i]
                            if val and not prev:
                                sink_idx = self.dial_sink_map[i]
                                if sink_idx == -1:
                                    try:
                                        subprocess.run(['pactl', 'set-sink-mute', '@DEFAULT_SINK@', 'toggle'], check=True, timeout=1)
                                        self.status_var.set(f'Toggled system mute (Dial {i+1})')
                                    except Exception as e:
                                        self.status_var.set(f'Error toggling system mute: {e}')
                                elif sink_idx is not None:
                                    try:
                                        subprocess.run(['pactl', 'set-sink-input-mute', str(sink_idx), 'toggle'], check=True, timeout=1)
                                        self.status_var.set(f'Toggled app mute (Dial {i+1})')
                                    except Exception as e:
                                        self.status_var.set(f'Error toggling app mute: {e}')
                            self.prev_buttons[i] = int(bool(val))
                        # always update UI display for buttons
                        self.button_vars[i].set('ON' if val else 'OFF')
                analogs = item.get('analogs')
                if analogs is not None:
                    for i, v in enumerate(analogs):
                        self.analog_vars[i].set(v)
        except queue.Empty:
            pass
        finally:
            # reschedule
            self.after(100, self._poll_queue)

    def save_log(self):
        if not self.log:
            self.status_var.set('No log data to save')
            return
        fn = filedialog.asksaveasfilename(defaultextension='.csv', filetypes=[('CSV','*.csv'),('All','*.*')])
        if not fn:
            return
        try:
            import csv

            with open(fn, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['timestamp', 'raw', 'first6', 'event_type', 'event_target', 'event_value', 'buttons', 'analogs'])
                for ts, item in self.log:
                    # format timestamp as ISO with ms
                    t = time.localtime(ts)
                    ms = int((ts - int(ts)) * 1000)
                    ts_str = time.strftime('%Y-%m-%dT%H:%M:%S', t) + f'.{ms:03d}'
                    buttons = item.get('buttons')
                    analogs = item.get('analogs')
                    buttons_s = '' if buttons is None else ','.join(str(int(bool(b))) for b in buttons)
                    analogs_s = '' if analogs is None else ','.join(str(int(a)) for a in analogs)
                    writer.writerow([
                        ts_str,
                        item.get('raw', ''),
                        item.get('first6', ''),
                        item.get('event_type', ''),
                        item.get('event_target', ''),
                        item.get('event_value', ''),
                        buttons_s,
                        analogs_s,
                    ])
            self.status_var.set(f'Saved log to {fn}')
        except Exception as e:
            self.status_var.set(f'Error saving log: {e}')

    def load_saved_dial_targets(self):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                targets = data.get('dial_targets')
                if isinstance(targets, list) and len(targets) == 4:
                    return targets
        except Exception:
            pass
        return ['System', 'None', 'None', 'None']

    def save_dial_targets(self):
        try:
            os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump({'dial_targets': [self.app_combobox_vars[i].get() for i in range(4)]}, f, indent=2)
        except Exception:
            pass

    def refresh_sink_inputs(self):
        """Refresh list of active application sink-inputs and update comboboxes."""
        try:
            p = subprocess.run(['pactl', 'list', 'sink-inputs'], capture_output=True, text=True, timeout=2)
            out = p.stdout
        except Exception:
            out = ''
        entries = []
        self.sink_input_map.clear()
        cur_idx = None
        cur_name = None
        for line in out.splitlines():
            m_idx = re.match(r'\s*Sink Input #(\d+)', line)
            if m_idx:
                if cur_idx is not None and cur_name:
                    disp = f"{cur_idx}: {cur_name}"
                    entries.append(disp)
                    self.sink_input_map[disp] = int(cur_idx)
                cur_idx = m_idx.group(1)
                cur_name = None
                continue
            if cur_idx is not None:
                m_app = re.match(r'\s*application.name\s*=\s*"(.+)"', line)
                if m_app:
                    cur_name = m_app.group(1)
                    continue
                m_media = re.match(r'\s*media.name\s*=\s*"(.+)"', line)
                if m_media and not cur_name:
                    cur_name = m_media.group(1)
                    continue
        # append last
        if cur_idx is not None and cur_name:
            disp = f"{cur_idx}: {cur_name}"
            entries.append(disp)
            self.sink_input_map[disp] = int(cur_idx)

        values = ['System', 'None'] + entries
        # update combobox values
        for i in range(4):
            cb = self.app_comboboxes[i]
            if cb is None:
                continue
            try:
                cb['values'] = values
            except Exception:
                pass
            cur = self.app_combobox_vars[i].get()
            if cur not in values:
                # clear mapping
                self.app_combobox_vars[i].set('None')
                self.dial_sink_map[i] = None
            else:
                # set mapping to current selection
                if cur == 'None':
                    self.dial_sink_map[i] = None
                elif cur == 'System':
                    self.dial_sink_map[i] = -1
                else:
                    self.dial_sink_map[i] = self.sink_input_map.get(cur)

        # schedule next refresh
        self.after(2000, self.refresh_sink_inputs)

    def on_app_selected(self, dial_index, event=None):
        """Handle user selection in combobox for dial_index."""
        try:
            sel = self.app_combobox_vars[dial_index].get()
            if sel == 'None':
                self.dial_sink_map[dial_index] = None
            elif sel == 'System':
                self.dial_sink_map[dial_index] = -1
            else:
                self.dial_sink_map[dial_index] = self.sink_input_map.get(sel)
            self.status_var.set(f'Dial {dial_index+1} mapped to {sel}')
            self.save_dial_targets()
        except Exception:
            pass

    def on_close(self):
        self.save_dial_targets()
        self.stop_event.set()
        time.sleep(0.2)
        self.destroy()


def main():
    app = App()
    app.mainloop()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print('Error:', e, file=sys.stderr)
        sys.exit(1)
