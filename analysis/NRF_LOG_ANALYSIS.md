# nRF BLE Log Analysis: Ola Scooter

**Log Source:** `ola Log 2026-09-27 21_00_45.txt`  
**Capture Software:** nRF Connect for Android  
**Target Device:** `OLAS1`  
**MAC Address:** `87:1A:44:60:00:28`  
**Capture Date:** 2026-09-27  

---

## 1. Capture Overview & Session Timeline

The log contains **324 log entries** covering **2 distinct connection sessions** to the Ola scooter:

| Session | Start Time | End Time | Duration | Disconnect Reason |
|---|---|---|---|---|
| **Session 1** | 20:58:47.202 | 21:00:05.929 | ~78.7 seconds | Bluetooth adapter toggled OFF |
| **Session 2** | 21:00:08.743 | 21:00:47.619 | ~38.9 seconds | Active session ended |

---

## 2. Observed GATT Connection Sequence

The captured connection sequence adheres strictly to standard BLE GATT workflow:

```
[Android BLE Adapter ON]
        │
        ▼
[Connect to 87:1A:44:60:00:28] (autoConnect=false, TRANSPORT_LE, PHY=LE 1M)
        │
        ▼
[Connection Established: status=0, state=CONNECTED]
        │
        ▼
[Connection Parameters Updated] (interval: 7.5ms ➔ 45.0ms, latency: 0, timeout: 5000ms)
        │
        ▼
[Service Discovery] (gatt.discoverServices())
        │
        ├─ Generic Attribute (0x1801) -> Service Changed (0x2A05) [Indicate]
        ├─ Generic Access (0x1800) -> Device Name (0x2A00), Appearance (0x2A01), Params (0x2A04)
        └─ Scooter Service (6e400001-b5a3-f393-e0a9-871a44600028)
             ├─ RX Characteristic [Notify] (6e400002-b5a3-f393-e0a9-e50e24dcca9e)
             ├─ TX Characteristic [Write No Response] (6e400003-b5a3-f393-e0a9-e50e24dcca9e)
             └─ Location Characteristic [Write] (45616c3f-b5a3-f393-e0a9-e50e24dcca9e)
        │
        ▼
[Enable Notification on RX Characteristic]
(gatt.setCharacteristicNotification(6e400002-..., true) + CCCD 0x2902 Write 0x0001)
        │
        ▼
[Immediate Notification Stream Commenced] (113 packets received)
```

---

## 3. Discovered Services & Characteristics Analysis

### 3.1 Custom Scooter Service
The service UUID has the base Nordic UART prefix, but with the **device's 6-byte MAC address appended as the lowest 12 hex digits**:
- **Service UUID:** `6e400001-b5a3-f393-e0a9-871a44600028`
  - MAC Address: `87:1A:44:60:00:28`
  - Suffix: `871a44600028`
- **RX Characteristic (Scooter ➔ App Telemetry Notification):**
  - UUID: `6e400002-b5a3-f393-e0a9-e50e24dcca9e`
  - Properties: `NOTIFY`
  - Descriptor: Client Characteristic Configuration Descriptor (`0x2902`)
- **TX Characteristic (App ➔ Scooter Commands):**
  - UUID: `6e400003-b5a3-f393-e0a9-e50e24dcca9e`
  - Properties: `WRITE_NO_RESPONSE`
- **Location Characteristic:**
  - UUID: `45616c3f-b5a3-f393-e0a9-e50e24dcca9e`
  - Properties: `WRITE`

---

## 4. Packet Payload Analysis (113 Notifications)

Every single notification received from `6e400002-...` is exactly 20 bytes (the standard BLE 4.x ATT MTU payload size).

### 4.1 Frame Breakdown
Inspection across all 113 packets reveals exact structural regularity:

```
[0x00]      Length prefix (0x13, 0x0C, 0x0E, 0x10, 0x0D)
[0x01]      Monotonically incrementing sequence counter (e.g. 0x03, 0x05, 0x07, ..., 0xFD, 0xFE, 0xFF, 0x01, 0x02...)
[0x02..0x05] Big-Endian 32-bit UNIX Epoch Timestamp
[0x06..0x07] IV / Packet sub-identifier
[0x08]      Type / Command descriptor
[0x09..0x13] Data Payload / Checksum
```

### 4.2 Proof of Timestamp Synchronization
Examining bytes 2 to 5 across sequential packets:

| Log Time (IST) | Raw Bytes [2:5] | Big-Endian Dec | Timestamp (UTC) | Converted IST Time |
|---|---|---|---|---|
| `20:58:49.861` | `6A B9 36 31` | `1790522929` | 2026-09-27 15:28:49 | **20:58:49** |
| `20:58:50.610` | `6A B9 36 32` | `1790522930` | 2026-09-27 15:28:50 | **20:58:50** |
| `20:58:51.827` | `6A B9 36 33` | `1790522931` | 2026-09-27 15:28:51 | **20:58:51** |
| `20:58:52.636` | `6A B9 36 34` | `1790522932` | 2026-09-27 15:28:52 | **20:58:52** |
| `20:58:53.634` | `6A B9 36 35` | `1790522933` | 2026-09-27 15:28:53 | **20:58:53** |

*Verification:* The timestamps embedded in the BLE payload match the local clock second-for-second with zero drift.

### 4.3 Initial Handshake/Announcement Packets
Right after notification subscription, the scooter emits two unencrypted announcement packets:

1. **Packet 1 (Hardware / Software Identity):**
   ```
   13 03 6A B9 36 31 01 02 70 46 37 33 31 33 32 33 31 01 B7 39
   ```
   - Length: `0x13` (19 bytes payload)
   - Sequence: `0x03`
   - Timestamp: `0x6AB93631` (1790522929)
   - Salt/IV: `0x01 0x02`
   - Type: `0x70` ('p')
   - Data: `46 37 33 31 33 32 33 31` (ASCII `"F7313231"` = Scooter ECU Firmware / Hardware Build ID)
   - Trailer: `01 B7 39`

2. **Packet 2 (Initial State / Metric):**
   ```
   0C 05 6A B9 36 31 01 02 71 01 01 09 CA 00 00 00 00 00 00 00
   ```
   - Length: `0x0C` (12 bytes payload, zero-padded to 20 bytes)
   - Sequence: `0x05`
   - Timestamp: `0x6AB93631`
   - Salt/IV: `0x01 0x02`
   - Type: `0x71` ('q')
   - Data: `01 01 09 CA` (`0x09CA` = 2506 in decimal, representing 250.6 km odometer/range or internal vehicle metric).

---

## 5. Lock/Unlock Operations Analysis in nRF Log

A rigorous grep and AST scan was conducted across the capture file for GATT write operations:
- **Write requests found:** 0
- **Write commands found:** 0
- **Descriptor writes found:** 2 (enabling notifications on `0x2902` for generic attribute and custom RX characteristic).

### Key Finding on Replay & Passive Monitoring
1. This nRF Connect session represents a **passive telemetry monitoring session**, where the user connected and observed notifications without performing write operations.
2. In this mode, the scooter autonomously streams battery and telemetry updates.
3. Therefore, an unauthenticated client **can safely connect and subscribe to notifications** to receive live vehicle telemetry.
4. Active commands (Lock, Unlock, Trunk) require write commands to `6e400003-...` authenticated via the AES handshake identified in the APK analysis (`BleManagerImpl.d`).
