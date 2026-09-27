"""
BLE Scanner component for discovering Ola Electric Scooters
"""

import asyncio
import logging
from typing import List, Optional
from bleak import BleakScanner
from app.bluetooth.models import ScooterDevice
from app.bluetooth.gatt import OLA_NUS_BASE_PREFIX

logger = logging.getLogger("bluetooth.scanner")

KNOWN_OLA_NAMES = ["OLAS1", "OLA S1", "OLA S1 PRO", "OLA S1 AIR", "OLA ELECTRIC"]

class BleScanner:
    def __init__(self, timeout: int = 10):
        self.timeout = timeout

    async def scan(self) -> List[ScooterDevice]:
        logger.info(f"Initiating BLE scan with timeout {self.timeout}s...")
        try:
            discovered = await BleakScanner.discover(timeout=self.timeout, return_adv=True)
            results: List[ScooterDevice] = []

            for dev, adv in discovered.values():
                name = dev.name or adv.local_name or "Unknown Device"
                is_ola = False

                if any(k in name.upper() for k in KNOWN_OLA_NAMES):
                    is_ola = True
                for s in (adv.service_uuids or []):
                    if s.lower().startswith(OLA_NUS_BASE_PREFIX):
                        is_ola = True
                        break

                device_model = ScooterDevice(
                    name=name,
                    address=dev.address,
                    rssi=adv.rssi,
                    is_ola=is_ola,
                    service_uuids=adv.service_uuids or []
                )
                results.append(device_model)

            # Prioritize Ola scooters, then sort by signal strength
            results.sort(key=lambda d: (d.is_ola, d.rssi), reverse=True)
            logger.info(f"Scan complete. Found {len(results)} devices ({sum(1 for d in results if d.is_ola)} Ola scooters).")
            return results

        except Exception as e:
            logger.error(f"Error during BLE scan: {e}")
            return []
