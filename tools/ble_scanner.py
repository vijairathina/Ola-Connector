#!/usr/bin/env python3
"""
Ola Scooter BLE Scanner & GATT Inspector
Phase 2 Standalone Utility

Scans for nearby BLE devices, identifies Ola electric scooters,
and safely inspects their advertised GATT services and characteristics.
"""

import asyncio
import sys
from bleak import BleakScanner, BleakClient

OLA_SERVICE_PREFIX = "6e400001-b5a3-f393-e0a9-"
KNOWN_OLA_NAMES = ["OLAS1", "OLA S1", "OLA S1 PRO", "OLA S1 AIR", "OLA ELECTRIC"]

def is_ola_scooter(device, advertisement_data) -> bool:
    name = (device.name or advertisement_data.local_name or "").upper()
    if any(k in name for k in KNOWN_OLA_NAMES):
        return True
    for uuid in (advertisement_data.service_uuids or []):
        if uuid.lower().startswith(OLA_SERVICE_PREFIX):
            return True
    return False

async def scan_devices(timeout: int = 10):
    print("=" * 60)
    print(f"Scanning for nearby BLE devices ({timeout}s timeout)...")
    print("=" * 60)

    devices = await BleakScanner.discover(timeout=timeout, return_adv=True)

    if not devices:
        print("\nNo BLE devices found.")
        print("\nTroubleshooting:")
        print("✓ Ensure Bluetooth is turned ON on your computer/Raspberry Pi")
        print("✓ Ensure scooter is nearby and awake (screen ON)")
        print("✓ Ensure no other phone/app is currently holding an active BLE connection")
        return []

    device_list = list(devices.values())
    print(f"\nFound {len(device_list)} device(s):\n")

    for i, (device, adv) in enumerate(device_list):
        name = device.name or adv.local_name or "Unknown"
        ola_tag = " [*** OLA SCOOTER DETECTED ***]" if is_ola_scooter(device, adv) else ""
        print(f"[{i + 1}] {name}{ola_tag}")
        print(f"    Address: {device.address}")
        print(f"    RSSI:    {adv.rssi} dBm")
        if adv.service_uuids:
            print(f"    Services:")
            for s in adv.service_uuids:
                print(f"      - {s}")
        if adv.manufacturer_data:
            print(f"    Manufacturer Data: { {k: v.hex() for k, v in adv.manufacturer_data.items()} }")
        print()

    return device_list

async def inspect_device(device):
    print("=" * 60)
    print(f"Connecting to {device.name or 'Device'} ({device.address})...")
    print("=" * 60)

    try:
        async with BleakClient(device) as client:
            connected = client.is_connected
            print(f"Connected: {connected}")
            print("\nDiscovering GATT Services & Characteristics...\n")

            for service in client.services:
                print(f"Service: {service.uuid} ({service.description})")
                for char in service.characteristics:
                    props = ", ".join(char.properties)
                    print(f"  Characteristic: {char.uuid} [{props}]")
                    if "read" in char.properties:
                        try:
                            val = await client.read_gatt_char(char.uuid)
                            print(f"    Value (Hex): {val.hex()} | Str: {val[:30]}")
                        except Exception as e:
                            print(f"    Read Error: {e}")
                    for desc in char.descriptors:
                        print(f"    Descriptor: {desc.uuid} ({desc.description})")
                print()

    except Exception as e:
        print(f"\nFailed to connect or discover services: {e}")
        print("Note: If scooter is paired with a phone, disconnect the phone first.")

async def main():
    timeout = 10
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        timeout = int(sys.argv[1])

    devices = await scan_devices(timeout=timeout)
    if not devices:
        return

    # Check if an Ola Scooter was detected
    ola_indices = [i for i, (dev, adv) in enumerate(devices) if is_ola_scooter(dev, adv)]
    
    print("-" * 60)
    selection = input(f"Select device number to inspect GATT [1-{len(devices)}] or 'q' to quit: ").strip()
    if selection.lower() == 'q' or not selection.isdigit():
        print("Exiting.")
        return

    idx = int(selection) - 1
    if 0 <= idx < len(devices):
        target_device = devices[idx][0]
        await inspect_device(target_device)
    else:
        print("Invalid selection.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nScan interrupted by user.")
