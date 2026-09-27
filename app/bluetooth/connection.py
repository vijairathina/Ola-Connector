"""
Low-level Bleak Connection Manager for Ola Electric Scooter
"""

import asyncio
import logging
from typing import Callable, Optional
from bleak import BleakClient
from app.bluetooth.gatt import (
    get_scooter_service_uuid,
    OLA_CHAR_RX_TELEMETRY,
    OLA_CHAR_TX_COMMANDS
)

logger = logging.getLogger("bluetooth.connection")

class BleConnection:
    def __init__(self, address: str, notification_callback: Callable[[bytes], None], on_disconnect: Optional[Callable[[], None]] = None):
        self.address = address
        self.notification_callback = notification_callback
        self.on_disconnect_callback = on_disconnect
        self.client: Optional[BleakClient] = None
        self._is_connected: bool = False

    @property
    def is_connected(self) -> bool:
        return self.client is not None and self.client.is_connected

    def _handle_disconnect(self, client: BleakClient):
        logger.warning(f"BLE Client disconnected from {self.address}")
        self._is_connected = False
        if self.on_disconnect_callback:
            try:
                self.on_disconnect_callback()
            except Exception as e:
                logger.error(f"Error in on_disconnect callback: {e}")

    def _handle_notification(self, sender, data: bytearray):
        try:
            self.notification_callback(bytes(data))
        except Exception as e:
            logger.error(f"Error in notification processing: {e}")

    async def connect(self, timeout: float = 15.0) -> bool:
        logger.info(f"Initiating BLE connection to scooter at {self.address} (timeout={timeout}s)...")
        try:
            # On Windows & Linux, discovering the BLEDevice object first ensures OS BLE cache is primed
            from bleak import BleakScanner
            logger.info(f"Resolving BLE device {self.address} from active advertisements...")
            device = await BleakScanner.find_device_by_address(self.address, timeout=min(8.0, timeout))
            
            target = device if device is not None else self.address
            if device:
                logger.info(f"Device resolved: {device.name} (RSSI: {getattr(device, 'rssi', 'N/A')} dBm)")
            else:
                logger.warning(f"Device {self.address} not seen in quick scan, attempting direct address connection...")

            self.client = BleakClient(
                target,
                disconnected_callback=self._handle_disconnect,
                timeout=timeout
            )
            await self.client.connect()
            self._is_connected = self.client.is_connected

            if not self._is_connected:
                logger.error("Bleak reported connect() completed but client is not connected.")
                return False

            logger.info("Connected successfully. Enabling telemetry notifications...")
            # Enable notification on RX characteristic
            await self.client.start_notify(OLA_CHAR_RX_TELEMETRY, self._handle_notification)
            logger.info(f"Subscribed to notifications on {OLA_CHAR_RX_TELEMETRY}")
            return True

        except Exception as e:
            err_str = str(e)
            logger.error(f"Connection to {self.address} failed: {type(e).__name__} ({err_str or 'No details'})")
            if "Unreachable" in err_str or "FAILED" in err_str or not err_str:
                logger.info("Diagnostics: Ola scooter requires BLE bonding/pairing before GATT services can be accessed.")
                logger.info("Ensure the scooter is paired in Windows Bluetooth Settings ('OLAS1') and scooter screen is active.")
            self._is_connected = False
            if self.client:
                try:
                    await self.client.disconnect()
                except Exception:
                    pass
                self.client = None
            return False

    async def disconnect(self):
        if self.client:
            logger.info(f"Disconnecting from {self.address}...")
            try:
                if self.is_connected:
                    try:
                        await self.client.stop_notify(OLA_CHAR_RX_TELEMETRY)
                    except Exception as e:
                        logger.debug(f"Error stopping notification: {e}")
                    await self.client.disconnect()
            except Exception as e:
                logger.error(f"Error during disconnect: {e}")
            finally:
                self.client = None
                self._is_connected = False
                logger.info("Disconnected cleanly.")

    async def write_command(self, payload: bytes) -> bool:
        if not self.is_connected:
            logger.error("Cannot write command: Client is not connected.")
            return False
        try:
            logger.info(f"Writing command to {OLA_CHAR_TX_COMMANDS}: {payload.hex()}")
            await self.client.write_gatt_char(OLA_CHAR_TX_COMMANDS, payload, response=False)
            return True
        except Exception as e:
            logger.error(f"Failed to write command: {e}")
            return False
