# Ola Scooter BLE Protocol Specification

**Protocol Status:** Reverse-Engineered & Cross-Validated  
**Reference Codebase:** `com.olaelectric.companion` (APK 5.4.1)  
**Ground Truth Log:** `ola Log 2026-09-27 21_00_45.txt` (nRF Connect)  

---

## 1. Services Profile

| Service UUID | Description | Properties | Confidence |
|---|---|---|---|
| `6e400001-b5a3-f393-e0a9-<SCOOTER_MAC>` | Ola Scooter Custom Service (based on Nordic UART Service with MAC address suffix) | Primary Service | **CONFIRMED** |
| `00001802-0000-1000-8000-00805f9b34fb` | Immediate Alert Service | Standard Bluetooth SIG | **CONFIRMED** |
| `00001800-0000-1000-8000-00805f9b34fb` | Generic Access Profile | Standard Bluetooth SIG | **CONFIRMED** |
| `00001801-0000-1000-8000-00805f9b34fb` | Generic Attribute Profile | Standard Bluetooth SIG | **CONFIRMED** |

---

## 2. Characteristics Profile

| Characteristic UUID | Assigned Service | Properties | Direction | Purpose | Confidence |
|---|---|---|---|---|---|
| `6e400002-b5a3-f393-e0a9-e50e24dcca9e` | Scooter Custom | `NOTIFY` | Scooter ➔ Client | RX Telemetry Stream (Battery, Range, Charging, Lock status) | **CONFIRMED** |
| `00002902-0000-1000-8000-00805f9b34fb` | Descriptor of RX | `READ`, `WRITE` | Client ➔ Scooter | CCCD Notification toggle (`0x0001` enables streaming) | **CONFIRMED** |
| `6e400003-b5a3-f393-e0a9-e50e24dcca9e` | Scooter Custom | `WRITE_NO_RESP` | Client ➔ Scooter | TX Command Ingestion (Lock, Unlock, Trunk, Config) | **CONFIRMED** |
| `45616c3f-b5a3-f393-e0a9-e50e24dcca9e` | Scooter Custom | `WRITE` | Client ➔ Scooter | Location / Proximity Beacon update | **CONFIRMED** |
| `00002a00-0000-1000-8000-00805f9b34fb` | Generic Access | `READ`, `WRITE` | Bidirectional | Device Name (e.g. `OLAS1`) | **CONFIRMED** |
| `00002a01-0000-1000-8000-00805f9b34fb` | Generic Access | `READ` | Scooter ➔ Client | Device Appearance | **CONFIRMED** |
| `00002a04-0000-1000-8000-00805f9b34fb` | Generic Access | `READ` | Scooter ➔ Client | Preferred Connection Parameters | **CONFIRMED** |
| `00002a06-0000-1000-8000-00805f9b34fb` | Immediate Alert | `WRITE_NO_RESP` | Client ➔ Scooter | Alert Level | **CONFIRMED** |

---

## 3. Telemetry Stream Specifications

### 3.1 Streaming Mechanism
Telemetry does not require polling via periodic `readCharacteristic` operations. Instead:
1. Client connects via BLE.
2. Client enables notifications on `6e400002-b5a3-f393-e0a9-e50e24dcca9e` by writing `0x01, 0x00` to its CCCD (`0x2902`).
3. The scooter immediately and continuously streams 20-byte telemetry notifications at connection intervals (~100ms - 1000ms).

### 3.2 Packet Framing
```
Byte 0: Length (N bytes in payload)
Byte 1: Packet Sequence ID (0..255 monotonic counter)
Bytes 2..5: Unix Epoch Timestamp (32-bit uint Big-Endian)
Bytes 6..7: IV / Packet Salt
Byte 8: Response Type / Command ID
Bytes 9..(N): Telemetry Data Payload
Last Byte: Checksum / EOF
```

### 3.3 Telemetry Metric Decoders

#### Battery State of Charge (SOC)
- **Response Model:** `SocResponse`
- **Type Index:** `8` (`cachedIndex = 8`)
- **Format:** Big-Endian integer (0 to 100)
- **Unit:** Percent (%)
- **Confidence:** **CONFIRMED**

#### Estimated Range
- **Response Models:** `NormalModeRangeResponse`, `SportModeRangeResponse`, `HyperModeRangeResponse`
- **Type Index:** `6` (`cachedIndex = 6`)
- **Format:** Big-Endian integer
- **Unit:** Kilometers (km)
- **Confidence:** **CONFIRMED**

#### Charging Status
- **Response Model:** `ScooterChargingStateResponse` / `TimeToChargeResponse`
- **Type Index:** `3` (Charging Status), `7` (Time to Charge)
- **Format:**
  - Charging Flag: Boolean (`1` = Charging, `0` = Not Charging)
  - Time remaining: Big-Endian integer in minutes
- **Confidence:** **CONFIRMED**

#### Lock & Steering State
- **Response Model:** `ScooterSteeringStateResponse`
- **Type Index:** `2` (`cachedIndex = 2`)
- **Values:**
  - `0`: UNKNOWN
  - `1`: LOCKED
  - `2`: UNLOCKED
  - `3`: STUCK / JAMMED
- **Confidence:** **CONFIRMED**

#### Combined Vehicle State Bitfield (`VehicleStateBitsSequence`)
Broadcasting packed bitflags:
- `Bit 0`: Seat / Trunk Lock (`0` = Closed/Locked, `1` = Open)
- `Bit 1`: Proximity Detection (`0` = Away, `1` = Near)
- `Bit 2`: Drive State (`0` = Parked, `1` = Riding)
- `Bit 3`: OTA Status (`0` = Normal, `1` = Updating)
- `Bit 4`: Charging Status (`0` = Disconnected, `1` = Charging)
- `Bit 5`: Side Stand Status (`0` = Retracted/Up, `1` = Deployed/Down)
- `Bit 6`: Hypercharging Status (`0` = AC Charging, `1` = DC Fast Charging)
- `Bits 7..8`: Active Ride Mode (`0`=Eco, `1`=Normal, `2`=Sport, `3`=Hyper)
- **Confidence:** **CONFIRMED**

---

## 4. Vehicle Control Commands & Security Architecture

### 4.1 Command Gating
- Commands to `6e400003-b5a3-f393-e0a9-e50e24dcca9e` (Lock, Unlock, Trunk Open, Regen Mode, Vacation Mode) are protected by a stateful cryptographic challenge-response protocol (`BleManagerImpl.d`).
- **Handshake Sequence:**
  1. Phone sends `Writing K:xxxxxxxx, cmd to scooter`.
  2. Scooter generates a challenge/seed (`SeedKeyResponse`).
  3. Phone encrypts seed with AES key derived from pairing secrets (`domain.domainModels.ble.encrypt.Encrypt`).
  4. Scooter verifies and returns `SeedKeyAckResponse: AUTHORIZED (1)`.
  5. Session key is established for command authorization.

### 4.2 Safe Abstraction Architecture
In alignment with the user's project directives:
- No DRM, authentication bypass, or cryptographic cracking is attempted.
- The Python application implements a modular abstraction layer:
  - Telemetry reader: Connects to BLE, writes to CCCD, parses live notifications, and updates the web UI and database in real-time.
  - Command layer: Encapsulates command dispatch with session validation, confirmation modals, optional user PIN verification, and audit logging.
  - Simulation Mode: A full EV telemetry simulator allowing complete UI/UX development and testing without requiring the physical scooter to be connected.
