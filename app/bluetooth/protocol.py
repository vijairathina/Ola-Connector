"""
Protocol Parser & Encoder for Ola Electric Scooter BLE Packets
Reverse-engineered from com.olaelectric.companion APK and verified with nRF captures.
"""

import time
from datetime import datetime
from typing import Optional, Dict, Any
from app.bluetooth.models import ScooterStatus
from app.bluetooth.gatt import (
    RESP_STEERING_LOCK_STATE,
    RESP_CHARGING_STATE,
    RESP_OTA_STATE,
    RESP_DRIVE_STATE,
    RESP_RANGE,
    RESP_TIME_TO_CHARGE,
    RESP_BATTERY_SOC,
    RESP_TIME_TO_HYPERCHARGE,
    LOCK_STATE_NAMES
)

class OlaProtocol:
    def __init__(self):
        self.sequence_id: int = 0

    def get_next_sequence_id(self) -> int:
        self.sequence_id = (self.sequence_id + 1) % 256
        return self.sequence_id

    def parse_notification(self, raw_bytes: bytes, current_status: ScooterStatus) -> ScooterStatus:
        """
        Parses a 20-byte BLE notification packet into the ScooterStatus model.
        Packet format:
          Byte 0: Payload length
          Byte 1: Monotonic sequence ID
          Bytes 2..5: Unix epoch timestamp in seconds (Big Endian)
          Bytes 6..7: Salt / IV
          Byte 8: Response Type / Command descriptor
          Bytes 9..N: Data payload
        """
        if not raw_bytes or len(raw_bytes) < 9:
            return current_status

        payload_len = raw_bytes[0]
        seq_id = raw_bytes[1]
        
        # Parse timestamp
        try:
            ts_seconds = int.from_bytes(raw_bytes[2:6], "big")
            pkt_time = datetime.fromtimestamp(ts_seconds).strftime("%Y-%m-%d %H:%M:%S")
            current_status.last_updated = pkt_time
            current_status.last_updated_timestamp = float(ts_seconds)
        except Exception:
            current_status.last_updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            current_status.last_updated_timestamp = time.time()

        resp_type = raw_bytes[8]
        effective_len = min(payload_len + 1, len(raw_bytes))
        data_payload = raw_bytes[9:effective_len]

        # 1. State of Charge (Battery %)
        if resp_type == RESP_BATTERY_SOC:
            if len(data_payload) >= 1:
                soc = int.from_bytes(data_payload[:1], "big")
                if 0 <= soc <= 100:
                    current_status.battery_percent = soc
                    if current_status.charging:
                        current_status.charging_percent = soc

        # 2. Estimated Range (km)
        elif resp_type == RESP_RANGE:
            if len(data_payload) >= 1:
                range_km = int.from_bytes(data_payload[:2], "big") if len(data_payload) >= 2 else data_payload[0]
                current_status.estimated_range_km = range_km

        # 3. Steering / Lock State
        elif resp_type == RESP_STEERING_LOCK_STATE:
            if len(data_payload) >= 1:
                lock_code = data_payload[0]
                current_status.lock_status = LOCK_STATE_NAMES.get(lock_code, "UNKNOWN")
                current_status.steering_status = current_status.lock_status

        # 4. Charging Status
        elif resp_type == RESP_CHARGING_STATE:
            if len(data_payload) >= 1:
                current_status.charging = bool(data_payload[0] != 0)
                if current_status.battery_percent is not None:
                    current_status.charging_percent = current_status.battery_percent

        # 5. Time to Charge
        elif resp_type == RESP_TIME_TO_CHARGE:
            if len(data_payload) >= 2:
                time_mins = int.from_bytes(data_payload[:2], "big")
                current_status.time_to_full_charge_min = time_mins
                current_status.charging = True

        # 6. Drive State
        elif resp_type == RESP_DRIVE_STATE:
            if len(data_payload) >= 1:
                state_code = data_payload[0]
                current_status.is_driving = bool(state_code == 1)

        # 7. Device Announcement / Initial Packets (e.g. 0x70, 0x71 from nRF captures)
        elif resp_type == 0x70:
            # Firmware / Hardware version string (e.g. "F7313231")
            pass
        elif resp_type == 0x71:
            # Combined vehicle telemetry snapshot
            if len(data_payload) >= 4:
                # Byte 2..3 in initial 0x71 packet represents 2506 (e.g. 250.6 km odometer/range)
                val = int.from_bytes(data_payload[2:4], "big")
                if val > 0:
                    current_status.odometer_km = round(val / 10.0, 1)

        return current_status

    def build_command_frame(self, cmd_type: int, payload: bytes = b"") -> bytes:
        """
        Builds a framed command packet adhering to the PktGenerator standard.
        Note: Command execution requires authenticated AES session on TX characteristic.
        """
        seq = self.get_next_sequence_id()
        ts = int(time.time()).to_bytes(4, "big")
        salt = b"\x01\x02"
        body = bytes([seq]) + ts + salt + bytes([cmd_type]) + payload
        length = len(body)
        return bytes([length]) + body
