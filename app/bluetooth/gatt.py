"""
GATT UUID Constants and Definitions for Ola Electric Scooters
Derived from static APK analysis (v5.4.1) and nRF BLE captures.
"""

# Base Nordic UART Service prefix
OLA_NUS_BASE_PREFIX = "6e400001-b5a3-f393-e0a9-"

def get_scooter_service_uuid(mac_address: str) -> str:
    """
    Ola dynamically binds the service UUID suffix to the device MAC address without colons.
    Example: MAC 87:1A:44:60:00:28 -> 6e400001-b5a3-f393-e0a9-871a44600028
    """
    clean_mac = mac_address.replace(":", "").replace("-", "").lower()
    return f"{OLA_NUS_BASE_PREFIX}{clean_mac}"

# Characteristics
OLA_CHAR_RX_TELEMETRY = "6e400002-b5a3-f393-e0a9-e50e24dcca9e"  # NOTIFY (Scooter -> App)
OLA_CHAR_TX_COMMANDS  = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"  # WRITE_NO_RESP (App -> Scooter)
OLA_CHAR_LOCATION     = "45616c3f-b5a3-f393-e0a9-e50e24dcca9e"  # WRITE
OLA_CHAR_LOCATION_ALT1 = "45616c4f-b5a3-f393-e0a9-e50e24dcca9e"
OLA_CHAR_LOCATION_ALT2 = "46616c3f-b5a3-f393-e0a9-e50e24dcca9e"

# Standard Bluetooth SIG UUIDs
UUID_CLIENT_CHAR_CONFIG = "00002902-0000-1000-8000-00805f9b34fb"  # CCCD
UUID_DEVICE_NAME        = "00002a00-0000-1000-8000-00805f9b34fb"
UUID_APPEARANCE         = "00002a01-0000-1000-8000-00805f9b34fb"
UUID_CONN_PARAMS        = "00002a04-0000-1000-8000-00805f9b34fb"
UUID_IMMEDIATE_ALERT    = "00001802-0000-1000-8000-00805f9b34fb"
UUID_ALERT_LEVEL        = "00002a06-0000-1000-8000-00805f9b34fb"

# Response Type IDs (as defined in APK domain/domainModels/ble/response)
RESP_STEERING_LOCK_STATE = 2
RESP_CHARGING_STATE      = 3
RESP_OTA_STATE           = 4
RESP_DRIVE_STATE         = 5
RESP_RANGE               = 6
RESP_TIME_TO_CHARGE      = 7
RESP_BATTERY_SOC         = 8
RESP_TIME_TO_HYPERCHARGE = 12

# Steering / Lock Hex states
LOCK_STATE_UNKNOWN     = 0
LOCK_STATE_LOCKED      = 1
LOCK_STATE_UNLOCKED    = 2
LOCK_STATE_STUCK       = 3

LOCK_STATE_NAMES = {
    0: "UNKNOWN",
    1: "LOCKED",
    2: "UNLOCKED",
    3: "STUCK"
}
