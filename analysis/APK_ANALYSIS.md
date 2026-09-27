# APK Analysis Report: Ola Electric Companion App

**App:** Ola Electric  
**Package:** `com.olaelectric.companion`  
**Version:** `5.4.1` (Version Code: `1344`)  
**Target SDK:** 34 | **Min SDK:** 24  
**Date of Analysis:** 2026-09-27  

---

## 1. Overview & Architecture

The Ola Electric Android companion application communicates with Ola scooters (S1 / S1 Pro / S1 Air / Gen 2) through a customized BLE (Bluetooth Low Energy) GATT architecture derived from the Nordic UART Service (NUS), layered with an internal packet framing protocol and AES-based cryptographic challenge-response authentication.

The architecture cleanly decouples:
1. **Bluetooth Transport Layer (`core.repo.ble.signal.manager.BleManagerImpl`)**: Handles GATT connection, service discovery, MTU negotiation, RSSI monitoring, and packet transmission.
2. **Packet Framing Layer (`domain.domainModels.ble.bytes.PktGenerator`)**: Encapsulates data into typed byte positions (`IdBytePosition`, `TimeBytePosition`, `IVBytePosition`, `TypeBytePosition`, `DataBytePosition`, `EOFBytePosition`).
3. **Telemetry & State Parser (`core.repo.ble.state.Parser` & `fr.a`)**: Translates incoming BLE notification streams into scooter telemetry models (`VehicleState`, `SocResponse`, `SportModeRangeResponse`, etc.).
4. **Security & Cryptography (`domain.domainModels.ble.encrypt.Encrypt` & `KeyGenerator`)**: Manages session keys, seed/key exchange, and AES encryption for vehicle control commands.

---

## 2. Android Manifest & Permissions

The application declares the following Bluetooth and Location permissions:

| Permission | Protection Level | Purpose |
|---|---|---|
| `android.permission.BLUETOOTH` | Normal | Legacy BLE communication (< Android 12) |
| `android.permission.BLUETOOTH_ADMIN` | Normal | Legacy BLE configuration & discovery |
| `android.permission.BLUETOOTH_SCAN` | Dangerous / Runtime | BLE discovery and advertisement filtering (Android 12+) |
| `android.permission.BLUETOOTH_CONNECT` | Dangerous / Runtime | Connecting to paired/discovered BLE devices (Android 12+) |
| `android.permission.ACCESS_FINE_LOCATION` | Dangerous / Runtime | Required for BLE beacon scanning and proximity detection |
| `android.permission.ACCESS_COARSE_LOCATION` | Dangerous / Runtime | Fallback location |

---

## 3. BLE Services & Characteristics Table

Cross-referencing the APK DEX bytecode with physical BLE observations:

| Service | Characteristic | UUID | Properties | Data Direction | Purpose | Confidence |
|---|---|---|---|---|---|---|
| **Scooter Telemetry & Control (Nordic UART Custom)** | Service | `6e400001-b5a3-f393-e0a9-<SCOOTER_MAC>` | - | - | Primary communication service for Ola Scooter. Notice suffix matches device MAC address (e.g. `871a44600028`). | **Confirmed** |
| | **RX (Telemetry Stream)** | `6e400002-b5a3-f393-e0a9-e50e24dcca9e` | `NOTIFY` | Scooter ➔ Client | Continuous broadcast of vehicle state, battery %, range, speed, charging, and lock status. | **Confirmed** |
| | **CCCD (Descriptor)** | `00002902-0000-1000-8000-00805f9b34fb` | `READ`, `WRITE` | Client ➔ Scooter | Enabling notifications (`0x0001`) starts telemetry stream without any handshake required. | **Confirmed** |
| | **TX (Command Ingestion)** | `6e400003-b5a3-f393-e0a9-e50e24dcca9e` | `WRITE_NO_RESPONSE` | Client ➔ Scooter | Sending authenticated vehicle commands (Lock, Unlock, Trunk, Regen, etc.). | **Confirmed** |
| | **Location / Proximity Tx** | `45616c3f-b5a3-f393-e0a9-e50e24dcca9e` | `WRITE` | Client ➔ Scooter | Location / proximity packet transmission. | **Confirmed** |
| | *Alternate Location UUID 1* | `45616c4f-b5a3-f393-e0a9-e50e24dcca9e` | `WRITE` | Client ➔ Scooter | Variant observed in APK fallback table. | **Confirmed** |
| | *Alternate Location UUID 2* | `46616c3f-b5a3-f393-e0a9-e50e24dcca9e` | `WRITE` | Client ➔ Scooter | Variant observed in APK fallback table. | **Confirmed** |
| **Immediate Alert** | Service | `00001802-0000-1000-8000-00805f9b34fb` | - | - | Standard BLE Immediate Alert Service. | **Confirmed** |
| | Alert Level | `00002a06-0000-1000-8000-00805f9b34fb` | `WRITE_NO_RESPONSE` | Client ➔ Scooter | Alert Level indication. | **Confirmed** |
| **Generic Attribute** | Service | `00001801-0000-1000-8000-00805f9b34fb` | - | - | Standard GATT Generic Attribute. | **Confirmed** |
| | Service Changed | `00002a05-0000-1000-8000-00805f9b34fb` | `INDICATE` | Scooter ➔ Client | GATT DB updates. | **Confirmed** |
| **Generic Access** | Service | `00001800-0000-1000-8000-00805f9b34fb` | - | - | Standard GATT Generic Access. | **Confirmed** |
| | Device Name | `00002a00-0000-1000-8000-00805f9b34fb` | `READ`, `WRITE` | Bidirectional | Advertised Name (e.g. `OLAS1`). | **Confirmed** |
| | Appearance | `00002a01-0000-1000-8000-00805f9b34fb` | `READ` | Scooter ➔ Client | Appearance code. | **Confirmed** |
| | Preferred Connection Params | `00002a04-0000-1000-8000-00805f9b34fb` | `READ` | Scooter ➔ Client | Interval 7.5ms - 45ms, latency 0, timeout 5000ms. | **Confirmed** |

---

## 4. Packet Framing & Data Formats

The APK uses a binary serialization model implemented in `domain.domainModels.ble.bytes.PktGenerator`:

### 4.1 Packet Framing Structure
```
┌───────────┬──────────────┬──────────────────┬─────────────────┬──────────────────┬──────────────────────┬─────────────┐
│ Byte 0    │ Byte 1       │ Bytes 2..5       │ Bytes 6..7      │ Byte 8           │ Bytes 9..(N-1)       │ Byte N      │
├───────────┼──────────────┼──────────────────┼─────────────────┼──────────────────┼──────────────────────┼─────────────┤
│ Length    │ Sequence ID  │ Unix Timestamp   │ IV / Salt       │ Response Type    │ Data Payload         │ EOF / CRC   │
│ (1 byte)  │ (1 byte)     │ (4 bytes BE uint)│ (2 bytes)       │ (1 byte uint)    │ (Variable length)    │ (1 byte)    │
└───────────┴──────────────┴──────────────────┴─────────────────┴──────────────────┴──────────────────────┴─────────────┘
```

1. **Byte 0 (Length)**: Total length of payload following this byte (e.g., `0x13` = 19 bytes, `0x0C` = 12 bytes). Sliced using `copyOfRange(1, length + 1)`.
2. **Byte 1 (`IdBytePosition`)**: Sequence number incremented modulo 256 for each packet.
3. **Bytes 2..5 (`TimeBytePosition`)**: 32-bit big-endian unsigned integer representing Unix epoch timestamp in seconds.
4. **Bytes 6..7 (`IVBytePosition`)**: 16-bit salt / IV used for packet identification / encryption alignment.
5. **Byte 8 (`TypeBytePosition`)**: Identifies response / telemetry message type.
6. **Bytes 9..N (`DataBytePosition`)**: Raw or encrypted data.
7. **End Byte (`EOFBytePosition`)**: Frame termination / checksum byte.

---

## 5. Telemetry & State Decoding (`domain.domainModels.ble.response`)

The APK maps responses using a `cachedIndex` integer lookup:

| Index | Response Class | Decoded Fields | Purpose & Values |
|---|---|---|---|
| **2** | `ScooterSteeringStateResponse` | `isLock()`, `isUnlock()`, `isStuck()`, `isUnknown()` | **Steering Lock State:**<br>`0`: UNKNOWN<br>`1`: LOCK<br>`2`: UNLOCK<br>`3`: STUCK |
| **3** | `ScooterChargingStateResponse` | `isCharging()`, `isSlowCharging()`, `isHyperCharging()` | **Charging Status:** boolean flag indicating active plug-in charging |
| **4** | `ScooterOTAStateResponse` | `isOTAAvailable()` | `0`: NO_OTA, `1`: OTA |
| **5** | `ScooterDriveStateResponse` | `isDriveState()`, `isParkState()` | Scooter motion state (`DRIVE`, `PARK`, `IDLE`) |
| **6** | `RangeResponse` (`NormalModeRangeResponse`, `SportModeRangeResponse`, `HyperModeRangeResponse`) | `getRange()` (Long) | **Estimated Range:** Extracted as big-endian integer, in kilometers |
| **7** | `TimeToChargeResponse` | `getTime()` (Long), `vehicleStateResponse` | Estimated minutes remaining until 100% full charge |
| **8** | `SocResponse` | `getSocValue()` (Long) | **Battery SOC (%):** Big-endian integer (0 to 100) |
| **12** | `TimeToHyperChargeResponse` | `timeToHyperCharge70`, `timeToFullHyperCharge` | Fast-charge estimated completion times |

### 5.1 Vehicle State Bitfield (`domain.domainModels.ble.bytes.VehicleStateBitsSequence`)
When telemetry packets broadcast combined status, bitwise indexing is used:
- **Bit 0**: `INDEX_SEAT_LOCK` (0 = Trunk Locked / Closed, 1 = Trunk Open)
- **Bit 1**: `INDEX_PROXIMITY` (0 = Outside proximity, 1 = Within proximity)
- **Bit 2**: `INDEX_DRIVE` (1 = Scooter in Drive mode, 0 = Parked)
- **Bit 3**: `INDEX_OTA_STATUS` (1 = OTA active)
- **Bit 4**: `INDEX_CHARGE_STATUS` (1 = Charger connected and charging, 0 = Disconnected)
- **Bit 5**: `INDEX_SIDE_STAND_STATUS` (1 = Side stand down/deployed, 0 = Side stand retracted)
- **Bit 6**: `INDEX_HYPER_CHARGE_STATUS` (1 = Hypercharger connected, 0 = Standard charging)
- **Bits 7..8**: `AVAILABLE_DRIVE_MODES` (Eco, Normal, Sport, Hyper)

---

## 6. Authentication & Security Observations

Inspection of `BleManagerImpl.d`, `domain.domainModels.ble.encrypt.Encrypt`, and `KeyGenerator` reveals:
1. **Challenge-Response Seed Authentication**:
   - The scooter does **not** accept unauthenticated commands on `6e400003-b5a3-f393-e0a9-e50e24dcca9e`.
   - Sequence:
     ```
     Phone ➔ Scooter: Step 2 "Writing K:xxxxxxxx, cmd to scooter"
     Scooter ➔ Phone: Step 3 Seed Key response (SeedKeyResponse)
     Phone ➔ Scooter: Step 3 "Sending AUTH key" (computed via AES with shared secret/PIN)
     Scooter ➔ Phone: Step 4 "Test AES Auth Success" (SeedKeyAckResponse: AUTHORIZED=1)
     ```
2. **Safe Vehicle Policy**:
   - In accordance with safety and legal directives, our Python local web application must **never** attempt to brute-force or defeat cryptographic protections.
   - Passive telemetry notifications on `6e400002-...` stream automatically without active authentication.
   - For commands (Lock, Unlock), our system will expose a clean, secure interface and PIN-protected abstraction that logs commands and safely handles authorization.
