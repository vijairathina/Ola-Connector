"""
Scooter Bluetooth Manager & Vehicle Telemetry State Controller
Includes full Live BLE handling and a realistic EV Simulation Mode.
"""

import asyncio
import logging
import threading
import time
import random
from datetime import datetime
from typing import Optional, List, Callable, Dict, Any

from app.bluetooth.models import ScooterStatus, ScooterDevice
from app.bluetooth.protocol import OlaProtocol
from app.bluetooth.scanner import BleScanner
from app.bluetooth.connection import BleConnection

logger = logging.getLogger("bluetooth.manager")

class ScooterBluetooth:
    def __init__(self, config: Dict[str, Any], simulation_mode: bool = False):
        self.config = config
        self.simulation_mode = simulation_mode
        self.protocol = OlaProtocol()
        self.scanner = BleScanner(timeout=config.get("bluetooth", {}).get("scan_timeout", 10))
        
        self.status = ScooterStatus(
            connected=False,
            is_simulated=simulation_mode
        )
        
        self.connection: Optional[BleConnection] = None
        self.target_address: Optional[str] = config.get("bluetooth", {}).get("device_address")
        self.auto_connect: bool = config.get("bluetooth", {}).get("auto_connect", True)
        self.reconnect_enabled: bool = config.get("bluetooth", {}).get("reconnect", True)
        self.reconnect_delay: int = config.get("bluetooth", {}).get("reconnect_delay", 5)

        self._listeners: List[Callable[[ScooterStatus], None]] = []
        self._lock = threading.Lock()
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._worker_thread: Optional[threading.Thread] = None
        self._sim_thread: Optional[threading.Thread] = None
        self._running: bool = False

    def add_listener(self, listener: Callable[[ScooterStatus], None]):
        with self._lock:
            if listener not in self._listeners:
                self._listeners.append(listener)

    def remove_listener(self, listener: Callable[[ScooterStatus], None]):
        with self._lock:
            if listener in self._listeners:
                self._listeners.remove(listener)

    def _notify_listeners(self):
        with self._lock:
            listeners = list(self._listeners)
        for listener in listeners:
            try:
                listener(self.status)
            except Exception as e:
                logger.error(f"Error calling status listener: {e}")

    def get_status(self) -> ScooterStatus:
        with self._lock:
            return self.status

    def start(self):
        self._running = True
        if self.simulation_mode:
            logger.info("Starting ScooterBluetooth in SIMULATION MODE...")
            self._start_simulation()
        else:
            logger.info("Starting ScooterBluetooth in LIVE BLE MODE...")
            self._start_ble_worker()

    def stop(self):
        self._running = False
        if self.connection and self._loop:
            asyncio.run_coroutine_threadsafe(self.connection.disconnect(), self._loop)

    # -------------------------------------------------------------
    # LIVE BLE WORKER & EVENT LOOP
    # -------------------------------------------------------------
    def _start_ble_worker(self):
        def run_loop():
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            self._loop.run_until_complete(self._auto_connect_loop())

        self._worker_thread = threading.Thread(target=run_loop, daemon=True, name="BLEWorker")
        self._worker_thread.start()

    async def _auto_connect_loop(self):
        while self._running:
            if not self.status.connected and self.auto_connect:
                address = self.target_address
                if not address:
                    logger.info("Auto-connect: Scanning for Ola Scooters...")
                    devices = await self.scanner.scan()
                    ola_devs = [d for d in devices if d.is_ola]
                    if ola_devs:
                        address = ola_devs[0].address
                        self.target_address = address
                        logger.info(f"Auto-selected scooter: {ola_devs[0].name} ({address})")

                if address:
                    await self._async_connect(address)

            await asyncio.sleep(self.reconnect_delay if self.reconnect_enabled else 10)

    async def _async_connect(self, address: str) -> bool:
        if self.connection and self.connection.is_connected:
            return True

        self.connection = BleConnection(
            address=address,
            notification_callback=self._on_ble_notification,
            on_disconnect=self._on_ble_disconnected
        )
        success = await self.connection.connect()
        with self._lock:
            self.status.connected = success
            if success:
                self.status.device_address = address
                self.status.device_name = "OLAS1"
                self.status.error_message = None
            else:
                self.status.error_message = (
                    "Scooter not found or connection refused.\n"
                    "Ensure Bluetooth is enabled, scooter is nearby and awake, "
                    "and official companion app is disconnected."
                )
        self._notify_listeners()
        return success

    def _on_ble_notification(self, raw_bytes: bytes):
        with self._lock:
            self.status = self.protocol.parse_notification(raw_bytes, self.status)
        self._notify_listeners()

    def ingest_telemetry_bytes(self, raw_bytes: bytes, device_name: str = "OLAS1", address: str = "87:1A:44:60:00:28"):
        """Ingests raw BLE telemetry packets received from phone Web Bluetooth."""
        with self._lock:
            self.status.connected = True
            self.status.device_name = device_name
            self.status.device_address = address
            self.status.error_message = None
            self.status = self.protocol.parse_notification(raw_bytes, self.status)
        self._notify_listeners()

    def _on_ble_disconnected(self):
        with self._lock:
            self.status.connected = False
            self.status.error_message = "Scooter disconnected."
        self._notify_listeners()

    # -------------------------------------------------------------
    # SIMULATION MODE
    # -------------------------------------------------------------
    def _start_simulation(self):
        with self._lock:
            self.status = ScooterStatus(
                connected=True,
                device_name="Ola S1 Pro (Simulated)",
                device_address="87:1A:44:60:00:28",
                rssi=-54,
                battery_percent=78,
                estimated_range_km=82,
                charging=False,
                charging_percent=78,
                time_to_full_charge_min=None,
                speed_kmh=0.0,
                odometer_km=1420.5,
                lock_status="LOCKED",
                steering_status="LOCKED",
                side_stand=True,
                driving_mode="NORMAL",
                is_driving=False,
                ota_status="NO_OTA",
                temperature_c=29.5,
                last_updated=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                last_updated_timestamp=time.time(),
                is_simulated=True
            )

        def run_sim():
            while self._running:
                time.sleep(3)
                with self._lock:
                    # Fluctuate RSSI realistically
                    self.status.rssi = random.randint(-62, -50)
                    self.status.last_updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    self.status.last_updated_timestamp = time.time()

                    # If charging, simulate battery gain
                    if self.status.charging:
                        if (self.status.battery_percent or 0) < 100:
                            if random.random() > 0.4:
                                self.status.battery_percent = (self.status.battery_percent or 0) + 1
                                self.status.charging_percent = self.status.battery_percent
                                self.status.estimated_range_km = int((self.status.battery_percent or 0) * 1.05)
                        if self.status.time_to_full_charge_min and self.status.time_to_full_charge_min > 1:
                            self.status.time_to_full_charge_min -= 1
                    else:
                        # Slight temperature fluctuation
                        self.status.temperature_c = round(28.0 + random.uniform(0.5, 2.0), 1)

                self._notify_listeners()

        self._sim_thread = threading.Thread(target=run_sim, daemon=True, name="EV-Simulator")
        self._sim_thread.start()

    # -------------------------------------------------------------
    # HIGH-LEVEL VEHICLE COMMAND METHODS
    # -------------------------------------------------------------
    async def scan(self) -> List[ScooterDevice]:
        if self.simulation_mode:
            return [
                ScooterDevice(
                    name="Ola S1 Pro (Simulated)",
                    address="87:1A:44:60:00:28",
                    rssi=-54,
                    is_ola=True,
                    service_uuids=["6e400001-b5a3-f393-e0a9-871a44600028"]
                )
            ]
        return await self.scanner.scan()

    async def connect(self, address: str) -> bool:
        if self.simulation_mode:
            with self._lock:
                self.status.connected = True
                self.status.device_address = address
                self.status.last_updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self._notify_listeners()
            return True

        if self._loop:
            fut = asyncio.run_coroutine_threadsafe(self._async_connect(address), self._loop)
            return fut.result()
        return False

    async def disconnect(self) -> bool:
        if self.simulation_mode:
            with self._lock:
                self.status.connected = False
            self._notify_listeners()
            return True

        if self.connection and self._loop:
            fut = asyncio.run_coroutine_threadsafe(self.connection.disconnect(), self._loop)
            fut.result()
            with self._lock:
                self.status.connected = False
            self._notify_listeners()
            return True
        return False

    async def lock(self) -> bool:
        logger.info("Executing vehicle command: LOCK")
        if self.simulation_mode:
            with self._lock:
                self.status.lock_status = "LOCKED"
                self.status.steering_status = "LOCKED"
                self.status.last_updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self._notify_listeners()
            return True

        if not self.status.connected or not self.connection:
            raise ConnectionError("Cannot send command: Scooter is not connected.")

        frame = self.protocol.build_command_frame(cmd_type=0x01, payload=b"\x01")
        fut = asyncio.run_coroutine_threadsafe(self.connection.write_command(frame), self._loop)
        return fut.result()

    async def unlock(self) -> bool:
        logger.info("Executing vehicle command: UNLOCK")
        if self.simulation_mode:
            with self._lock:
                self.status.lock_status = "UNLOCKED"
                self.status.steering_status = "UNLOCKED"
                self.status.last_updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self._notify_listeners()
            return True

        if not self.status.connected or not self.connection:
            raise ConnectionError("Cannot send command: Scooter is not connected.")

        frame = self.protocol.build_command_frame(cmd_type=0x01, payload=b"\x02")
        fut = asyncio.run_coroutine_threadsafe(self.connection.write_command(frame), self._loop)
        return fut.result()

    def toggle_simulation_charging(self, enable: bool):
        if self.simulation_mode:
            with self._lock:
                self.status.charging = enable
                if enable:
                    self.status.time_to_full_charge_min = max(5, int((100 - (self.status.battery_percent or 78)) * 1.5))
                else:
                    self.status.time_to_full_charge_min = None
            self._notify_listeners()
