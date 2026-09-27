#!/usr/bin/env python3
"""
Ola Scooter Bluetooth Web Controller - Application Entry Point
Supports Live BLE mode and realistic EV Telemetry Simulator mode (--simulation).
"""

import argparse
import sys
import logging
from app import create_app

def parse_args():
    parser = argparse.ArgumentParser(description="Ola Scooter Bluetooth Web Controller")
    parser.add_argument(
        "--simulation", "-s",
        action="store_true",
        help="Run in EV Simulator mode (develop and test without the physical vehicle)"
    )
    parser.add_argument(
        "--host",
        type=str,
        default=None,
        help="Custom host to bind (overrides config.yaml)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Custom port to bind (overrides config.yaml)"
    )
    parser.add_argument(
        "--config",
        type=str,
        default="config.yaml",
        help="Path to YAML configuration file"
    )
    return parser.parse_args()

def main():
    args = parse_args()
    app = create_app(config_path=args.config, simulation_mode=args.simulation)
    
    cfg = app.config.get("APP_CONFIG", {})
    host = args.host or cfg.get("server", {}).get("host", "127.0.0.1")
    port = args.port or cfg.get("server", {}).get("port", 5000)
    debug = cfg.get("server", {}).get("debug", False)

    print("=" * 65)
    print("      OLA SCOOTER BLUETOOTH WEB CONTROLLER")
    print("=" * 65)
    print(f"Mode:         {'SIMULATION (EV Simulator Active)' if args.simulation else 'LIVE BLE (Hardware Mode)'}")
    print(f"URL:          http://{host}:{port}")
    print(f"Target MAC:   {cfg.get('bluetooth', {}).get('device_address', 'Auto-discovery')}")
    print(f"Credentials:  admin / admin123 (Default PIN: 1234)")
    print("=" * 65)
    print("Press Ctrl+C to terminate cleanly.\n")

    try:
        app.run(host=host, port=port, debug=debug, threaded=True)
    except KeyboardInterrupt:
        print("\nShutting down controller...")
    finally:
        bt = app.config.get("BLUETOOTH")
        if bt:
            bt.stop()

if __name__ == "__main__":
    main()
