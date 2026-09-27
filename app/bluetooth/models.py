from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional, Dict, Any

@dataclass
class ScooterDevice:
    name: str
    address: str
    rssi: int
    is_ola: bool = False
    service_uuids: list = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "address": self.address,
            "rssi": self.rssi,
            "is_ola": self.is_ola,
            "service_uuids": self.service_uuids or []
        }

@dataclass
class ScooterStatus:
    connected: bool = False
    device_name: Optional[str] = None
    device_address: Optional[str] = None
    rssi: Optional[int] = None
    battery_percent: Optional[int] = None
    estimated_range_km: Optional[int] = None
    charging: Optional[bool] = None
    charging_percent: Optional[int] = None
    time_to_full_charge_min: Optional[int] = None
    speed_kmh: Optional[float] = None
    odometer_km: Optional[float] = None
    lock_status: Optional[str] = None  # "LOCKED", "UNLOCKED", "STUCK", "UNKNOWN"
    steering_status: Optional[str] = None
    side_stand: Optional[bool] = None
    driving_mode: Optional[str] = None  # "ECO", "NORMAL", "SPORT", "HYPER"
    is_driving: Optional[bool] = None
    ota_status: Optional[str] = None
    temperature_c: Optional[float] = None
    last_updated: Optional[str] = None
    last_updated_timestamp: Optional[float] = None
    error_message: Optional[str] = None
    is_simulated: bool = False

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        return d
