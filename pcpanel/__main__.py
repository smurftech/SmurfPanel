from __future__ import annotations

import argparse
import logging
from pathlib import Path

from pcpanel.audio import PactlAudioBackend
from pcpanel.config import AppConfig, config_to_json, default_config_path, save_config
from pcpanel.controller import Controller
from pcpanel.diagnostics import format_diagnostics, run_diagnostics


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the SmurfPanel controller")
    parser.add_argument("-v", "--verbose", action="store_true", help="enable debug logging")
    parser.add_argument(
        "--diagnose",
        action="store_true",
        help="check USB detection and required system commands, then exit",
    )
    parser.add_argument(
        "--config",
        type=Path,
        help="load a specific config file instead of ~/.config/pcpanel/config.json",
    )
    parser.add_argument(
        "--init-config",
        action="store_true",
        help="write a default config file and exit",
    )
    parser.add_argument(
        "--print-default-config",
        action="store_true",
        help="print the default config JSON and exit",
    )
    parser.add_argument(
        "--list-streams",
        action="store_true",
        help="list active application audio streams and exit",
    )
    parser.add_argument(
        "--test-volume",
        type=int,
        metavar="PERCENT",
        help="set dial 1 target to a test percentage and exit",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    config_path = args.config or default_config_path()
    if args.diagnose:
        checks = run_diagnostics()
        print(format_diagnostics(checks))
        if not all(check.ok for check in checks):
            raise SystemExit(1)
        return
    if args.print_default_config:
        print(config_to_json(AppConfig()))
        return
    if args.init_config:
        save_config(AppConfig(), config_path)
        print(f"Wrote config to {config_path}")
        return
    if args.list_streams:
        streams = PactlAudioBackend().list_streams()
        if not streams:
            print("No active application streams found.")
            return
        for stream in streams:
            binary = f" binary={stream.binary}" if stream.binary else ""
            volume = f" volume={stream.volume}%" if stream.volume is not None else ""
            muted = f" muted={stream.muted}" if stream.muted is not None else ""
            print(f"{stream.id}: {stream.name}{binary}{volume}{muted}")
        return

    controller = Controller(config_path=config_path)
    if args.test_volume is not None:
        value = round(max(0, min(100, args.test_volume)) * 255 / 100)
        controller.inject_dial(control_index=0, value=value)
        return
    controller.run_forever()


if __name__ == "__main__":
    main()
