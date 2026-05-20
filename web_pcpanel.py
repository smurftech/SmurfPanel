#!/usr/bin/env python3
import json
import logging
import os
import re
import sys
import queue
import threading
import time
import subprocess
import usb.core
import usb.util
import errno

logging.getLogger('usb').setLevel(logging.CRITICAL)
logging.getLogger('usb.core').setLevel(logging.CRITICAL)
logging.getLogger('usb.backend.libusb1').setLevel(logging.CRITICAL)

CONFIG_FILE = os.path.expanduser('~/.config/pcpanel_gui/mappings.json')
HTML_FILE = os.path.join(os.path.dirname(__file__), 'webview_ui.html')

VENDOR_ID = 0x0483
PRODUCT_ID = 0xa3c4
READ_TIMEOUT = 500


def find_device():
    dev = usb.core.find(idVendor=VENDOR_ID, idProduct=PRODUCT_ID)
    if dev is None:
        raise RuntimeError('Device not found')
    return dev


def parse_report(data_bytes):
    raw_hex = data_bytes.hex()
    parsed = {
        'raw': raw_hex,
        'first6': raw_hex[:6],
        'event_type': None,
        'event_target': None,
        'event_value': None,
        'buttons': [],
        'analogs': [],
    }

    if len(data_bytes) >= 1:
        b0 = data_bytes[0]
        parsed['buttons'] = [(b0 >> i) & 1 for i in range(4)]

    if len(data_bytes) >= 5:
        parsed['analogs'] = [int(data_bytes[i]) for i in range(1, 5)]
    elif len(data_bytes) > 1:
        parsed['analogs'] = [int(data_bytes[i]) for i in range(1, len(data_bytes))]

    if any(parsed['analogs']):
        parsed['event_type'] = 'dial'
        # choose first nonzero analog as the active dial event for summary
        for idx, val in enumerate(parsed['analogs']):
            if val is not None and val != 0:
                parsed['event_target'] = f'Dial {idx + 1}'
                parsed['event_value'] = val
                break

    if any(parsed['buttons']):
        parsed['event_type'] = 'button'
        parsed['event_target'] = 'Buttons'
        parsed['event_value'] = int(parsed['buttons'][0])

    return parsed


def parse_pactl_volume(stdout):
    match = re.search(r'([0-9]+)%', stdout)
    if match:
        return int(match.group(1))
    return None


def parse_pactl_mute(stdout):
    match = re.search(r'Mute:\s*(yes|no)', stdout, re.IGNORECASE)
    if match:
        return match.group(1).lower() == 'yes'
    return None


def get_system_volume():
    try:
        result = subprocess.run(['pactl', 'get-sink-volume', '@DEFAULT_SINK@'], capture_output=True, text=True, timeout=2)
        return parse_pactl_volume(result.stdout)
    except Exception:
        return None


def get_system_mute():
    try:
        result = subprocess.run(['pactl', 'get-sink-mute', '@DEFAULT_SINK@'], capture_output=True, text=True, timeout=2)
        return parse_pactl_mute(result.stdout)
    except Exception:
        return None


def list_sink_inputs():
    try:
        result = subprocess.run(['pactl', 'list', 'sink-inputs'], capture_output=True, text=True, timeout=2)
        out = result.stdout
    except Exception:
        return []

    entries = []
    current = None
    for line in out.splitlines():
        idx_match = re.match(r'\s*Sink Input #(\d+)', line)
        if idx_match:
            if current is not None:
                entries.append(current)
            current = {'id': int(idx_match.group(1)), 'name': None, 'volume': None, 'mute': None}
            continue
        if current is None:
            continue
        app_match = re.match(r'\s*application.name\s*=\s*"(.+)"', line)
        if app_match:
            current['name'] = app_match.group(1)
            continue
        media_match = re.match(r'\s*media.name\s*=\s*"(.+)"', line)
        if media_match and not current['name']:
            current['name'] = media_match.group(1)
            continue
        vol_match = re.match(r'\s*Volume:.*?([0-9]+)%', line)
        if vol_match and current['volume'] is None:
            current['volume'] = int(vol_match.group(1))
            continue
        mute_match = re.match(r'\s*Mute:\s*(yes|no)', line, re.IGNORECASE)
        if mute_match:
            current['mute'] = mute_match.group(1).lower() == 'yes'
            continue
    if current is not None:
        entries.append(current)
    for entry in entries:
        if not entry['name']:
            entry['name'] = f'Sink {entry["id"]}'
    return entries


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
            try:
                self.dev.set_configuration()
            except usb.core.USBError as e:
                if getattr(e, 'errno', None) == errno.EBUSY:
                    for cfg in self.dev:
                        for interface in cfg:
                            intf_num = interface.bInterfaceNumber
                            try:
                                if self.dev.is_kernel_driver_active(intf_num):
                                    self.dev.detach_kernel_driver(intf_num)
                            except Exception:
                                pass
                    try:
                        self.dev.set_configuration()
                    except Exception:
                        return
                else:
                    return
            cfg = self.dev.get_active_configuration()
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
                return
            try:
                if self.dev.is_kernel_driver_active(self.intf):
                    self.dev.detach_kernel_driver(self.intf)
                usb.util.claim_interface(self.dev, self.intf)
            except Exception:
                return

            max_packet = self.endpoint.wMaxPacketSize
            while not self.stop_event.is_set():
                try:
                    data = self.dev.read(self.endpoint.bEndpointAddress, max_packet, timeout=READ_TIMEOUT)
                    parsed = parse_report(bytes(data))
                    self.out_q.put(parsed)
                except usb.core.USBError as e:
                    if getattr(e, 'errno', None) in (errno.ETIMEDOUT, None):
                        continue
                    break
                except Exception:
                    break
        finally:
            if self.dev and self.intf is not None:
                try:
                    usb.util.release_interface(self.dev, self.intf)
                    self.dev.attach_kernel_driver(self.intf)
                except Exception:
                    pass
                try:
                    usb.util.dispose_resources(self.dev)
                except Exception:
                    pass


class WebAPI:
    def __init__(self):
        self.lock = threading.Lock()
        self.selected_targets = self.load_saved_dial_targets()
        self.dial_sink_map = [-1, None, None, None]
        self.sink_input_map = {}
        self.sink_inputs = []
        self.app_options = []
        self.raw_events = []
        self.raw_event_limit = 100
        self.prev_analogs = [None, None, None, None]
        self.prev_buttons = [0, 0, 0, 0]
        self.latest_event = {
            'event_type': None,
            'event_target': None,
            'event_value': None,
            'raw': None,
            'buttons': [0, 0, 0, 0],
            'analogs': [0, 0, 0, 0],
        }
        self.system_volume = None
        self.system_muted = None
        self.stop_event = threading.Event()
        self.out_q = queue.Queue()
        self.update_sink_inputs()
        self.reader = USBReaderThread(self.out_q, self.stop_event)
        self.reader.start()
        self.state_thread = threading.Thread(target=self._state_loop, daemon=True)
        self.state_thread.start()

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
                json.dump({'dial_targets': self.selected_targets}, f, indent=2)
        except Exception:
            pass

    def process_input_event(self, item):
        analogs = item.get('analogs') or []
        buttons = item.get('buttons') or []

        if analogs:
            for dial_index, value in enumerate(analogs[:4]):
                if value is None:
                    continue
                prev = self.prev_analogs[dial_index]
                if prev is None:
                    self.prev_analogs[dial_index] = value
                    continue
                if value != prev:
                    percent = int(value * 100 / 255)
                    sink_idx = self.dial_sink_map[dial_index]
                    if sink_idx == -1:
                        subprocess.run(['pactl', 'set-sink-volume', '@DEFAULT_SINK@', f'{percent}%'], check=False, timeout=2)
                    elif sink_idx is not None:
                        subprocess.run(['pactl', 'set-sink-input-volume', str(sink_idx), f'{percent}%'], check=False, timeout=2)
                    self.prev_analogs[dial_index] = value

        if buttons:
            for idx, val in enumerate(buttons[:4]):
                prev = self.prev_buttons[idx]
                if val and not prev:
                    sink_idx = self.dial_sink_map[idx]
                    if sink_idx == -1:
                        subprocess.run(['pactl', 'set-sink-mute', '@DEFAULT_SINK@', 'toggle'], check=False, timeout=2)
                    elif sink_idx is not None:
                        subprocess.run(['pactl', 'set-sink-input-mute', str(sink_idx), 'toggle'], check=False, timeout=2)
                self.prev_buttons[idx] = int(bool(val))

    def _state_loop(self):
        while not self.stop_event.is_set():
            try:
                item = self.out_q.get(timeout=0.5)
                with self.lock:
                    self.process_input_event(item)
                    self.latest_event.update(item)
                    self.raw_events.append({
                        'timestamp': time.time(),
                        'raw': item.get('raw'),
                        'first6': item.get('first6'),
                        'event_type': item.get('event_type'),
                        'event_target': item.get('event_target'),
                        'event_value': item.get('event_value'),
                        'buttons': item.get('buttons'),
                        'analogs': item.get('analogs'),
                    })
                    if len(self.raw_events) > self.raw_event_limit:
                        self.raw_events = self.raw_events[-self.raw_event_limit:]
            except Exception:
                pass
            time.sleep(0.1)

    def get_raw_events(self):
        with self.lock:
            return {'raw_events': list(self.raw_events)}

    def clear_raw_events(self):
        with self.lock:
            self.raw_events = []
        return {'success': True}

    def update_sink_inputs(self):
        with self.lock:
            entries = list_sink_inputs()
            self.sink_inputs = entries
            self.sink_input_map = {f"{entry['id']}: {entry['name']}": entry['id'] for entry in entries}
            self.app_options = ['System', 'None'] + [f"{entry['id']}: {entry['name']}" for entry in entries]
            for target in self.selected_targets:
                if target not in self.app_options and target not in ['System', 'None']:
                    self.app_options.append(target)
            self.update_dial_sink_map()

    def update_dial_sink_map(self):
        self.dial_sink_map = []
        for target in self.selected_targets:
            if target == 'System':
                self.dial_sink_map.append(-1)
            elif target == 'None':
                self.dial_sink_map.append(None)
            else:
                self.dial_sink_map.append(self.sink_input_map.get(target))

    def get_state(self):
        self.update_sink_inputs()
        self.system_volume = get_system_volume()
        self.system_muted = get_system_mute()
        dial_states = []
        for idx, target in enumerate(self.selected_targets):
            sink_idx = self.dial_sink_map[idx]
            if target == 'System' or sink_idx == -1:
                dial_states.append({
                    'target': 'System',
                    'volume': self.system_volume,
                    'mute': self.system_muted,
                    'type': 'system',
                })
            elif target == 'None' or sink_idx is None:
                dial_states.append({
                    'target': 'None',
                    'volume': None,
                    'mute': None,
                    'type': 'none',
                })
            else:
                stream = next((s for s in self.sink_inputs if s['id'] == sink_idx), None)
                dial_states.append({
                    'target': target,
                    'volume': stream['volume'] if stream else None,
                    'mute': stream['mute'] if stream else None,
                    'type': 'app',
                })
        with self.lock:
            return {
                'targets': self.selected_targets,
                'options': self.app_options,
                'system_volume': self.system_volume,
                'system_muted': self.system_muted,
                'latest_event': self.latest_event,
                'dial_states': dial_states,
                'sink_inputs': self.sink_inputs,
                'raw_events': self.raw_events[-20:],
            }

    def set_target(self, dial_index, target):
        try:
            dial_index = int(dial_index)
        except ValueError:
            return {'success': False, 'message': 'Invalid dial index'}

        if dial_index < 0 or dial_index >= 4:
            return {'success': False, 'message': 'Dial index out of range'}

        with self.lock:
            self.selected_targets[dial_index] = target
            self.update_dial_sink_map()
            self.save_dial_targets()
        return {'success': True}

    def stop(self):
        self.stop_event.set()
        self.reader.stop_event.set()
        return {'success': True}

    def toggle_mute(self, dial_index):
        try:
            dial_index = int(dial_index)
        except ValueError:
            return {'success': False, 'message': 'Invalid dial index'}

        if dial_index < 0 or dial_index >= 4:
            return {'success': False, 'message': 'Dial index out of range'}

        with self.lock:
            target = self.selected_targets[dial_index]
            sink_idx = self.dial_sink_map[dial_index]

        if target == 'System' or sink_idx == -1:
            try:
                subprocess.run(['pactl', 'set-sink-mute', '@DEFAULT_SINK@', 'toggle'], check=True, timeout=2)
                return {'success': True}
            except Exception as exc:
                return {'success': False, 'message': str(exc)}
        elif sink_idx is not None:
            try:
                subprocess.run(['pactl', 'set-sink-input-mute', str(sink_idx), 'toggle'], check=True, timeout=2)
                return {'success': True}
            except Exception as exc:
                return {'success': False, 'message': str(exc)}

        return {'success': False, 'message': 'No target selected for mute toggle'}


def load_html():
    try:
        with open(HTML_FILE, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as exc:
        raise RuntimeError(f'Unable to load HTML file: {exc}')


def main():
    try:
        import webview
    except ImportError:
        print('pywebview is required. Install it with `pip install pywebview`.')
        sys.exit(1)

    api = WebAPI()
    html = load_html()
    window = webview.create_window('PCPanel Webview', html=html, js_api=api, width=900, height=720)

    preferred_backends = ['gtk', 'qt']
    if os.environ.get('WAYLAND_DISPLAY') or os.environ.get('XDG_SESSION_TYPE') == 'wayland':
        preferred_backends = ['qt', 'gtk']

    for gui_backend in preferred_backends:
        try:
            print(f'Starting pywebview with {gui_backend} backend...')
            webview.start(gui=gui_backend)
            return
        except Exception as exc:
            print(f'{gui_backend.upper()} backend unavailable: {exc}')

    print('No supported webview backend is available.')
    print('Install a supported backend:')
    print('  pip install pywebview[gtk] PyGObject')
    print('or')
    print('  pip install pywebview[qt] qtpy PySide6')
    sys.exit(1)


if __name__ == '__main__':
    main()
