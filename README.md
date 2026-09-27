# Ola Scooter Bluetooth Web Controller

A lightweight, local Python web application designed for Linux and **Raspberry Pi (3, 4, 5)** that communicates with an **Ola Electric Scooter** over Bluetooth Low Energy (BLE) to provide a modern, real-time EV telemetry cockpit and control dashboard.

---

## Features

- **Real-Time EV Telemetry**: Live battery percentage, estimated range (km), charging status, and handle lock state.
- **Sub-Second Live Updates**: Uses Server-Sent Events (SSE) to update the dashboard reactively without page reloads.
- **Safety-First Vehicle Commands**: [ LOCK ] and [ UNLOCK ] buttons with confirmation dialogs, audit logging, and security PIN verification.
- **EV Telemetry Simulator (`--simulation`)**: Complete realistic hardware simulation mode allowing full UI/UX development and testing without needing the scooter nearby.
- **Standalone BLE Scanner**: CLI utility (`tools/ble_scanner.py`) to discover and inspect GATT services on nearby Ola scooters.
- **Local SQLite Storage**: Records battery discharge trends, charging sessions, bluetooth connection logs, and command audits.
- **Raspberry Pi Native**: Extremely lightweight (Vanilla CSS, zero heavy frontend framework bloat), with automated `install.sh`, systemd daemon, and management scripts.

---

## Architecture Overview

```
Ola Scooter (ECU)
       │ (BLE GATT - Nordic UART Variant)
       ▼
Bleak Connection Layer (`app/bluetooth/connection.py`)
       │
Telemetry Packet Parser (`app/bluetooth/protocol.py`)
       │
Bluetooth State Manager (`app/bluetooth/manager.py`)
  ├── SQLite Database (`app/database.py`)
  └── Server-Sent Events (SSE) Stream (`/api/scooter/events`)
       │
EV Cockpit Web Dashboard (`app/templates/dashboard.html`)
```

---

## 1. Quick Start (Local / Simulation Mode)

### Step 1: Set Up Python Virtual Environment
```bash
# Windows
python -m venv venv
.\venv\Scripts\pip install -r requirements.txt

# Linux / Raspberry Pi
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
```

### Step 2: Run in EV Simulation Mode
```bash
# Windows
.\venv\Scripts\python run.py --simulation

# Linux / Raspberry Pi
./venv/bin/python run.py --simulation
```

Open your browser to:
👉 **`http://127.0.0.1:5000`**

- **Username:** `admin`
- **Password:** `admin123`
- **Vehicle Security PIN:** `1234`

---

## 2. Hardware Mode (Connecting to Physical Scooter)

### Step 1: Scan for Your Scooter
Run the scanner tool to identify your scooter's BLE address:
```bash
# Windows
.\venv\Scripts\python tools/ble_scanner.py

# Linux / Raspberry Pi
./venv/bin/python tools/ble_scanner.py
```
Your Ola scooter will appear as `OLAS1` or with a service beginning with `6e400001-b5a3-f393-e0a9-...` (e.g., `87:1A:44:60:00:28`).

### Step 2: Configure Address
Update `config.yaml`:
```yaml
bluetooth:
  device_address: "87:1A:44:60:00:28"
  auto_connect: true
  reconnect: true
  reconnect_delay: 5
```

### Step 3: Run the Live Controller
```bash
./venv/bin/python run.py
```

---

## 3. Raspberry Pi Systemd Deployment

### Automated Installation
```bash
chmod +x install.sh start.sh stop.sh status.sh
./install.sh
```

### Service Management
```bash
# Check service status and recent journal logs
./status.sh

# Stop the service
./stop.sh

# Start the service
./start.sh
```

Or standard systemd commands:
```bash
sudo systemctl status ola-scooter-web
sudo journalctl -u ola-scooter-web -f
```

---

## 4. BLE Protocol & GATT Specification

| Service / Characteristic | UUID | Properties | Purpose |
|---|---|---|---|
| **Scooter Custom Service** | `6e400001-b5a3-f393-e0a9-<MAC>` | - | Dynamic UUID ending in scooter MAC |
| **RX Telemetry Stream** | `6e400002-b5a3-f393-e0a9-e50e24dcca9e` | `NOTIFY` | 20-byte periodic telemetry packets |
| **CCCD Descriptor** | `00002902-0000-1000-8000-00805f9b34fb` | `WRITE` | Write `0x0001` to start stream |
| **TX Command Ingestion** | `6e400003-b5a3-f393-e0a9-e50e24dcca9e` | `WRITE_NO_RESP` | Authenticated vehicle commands |
| **Location Tx** | `45616c3f-b5a3-f393-e0a9-e50e24dcca9e` | `WRITE` | Proximity & beaconing data |

### Telemetry Packet Framing (20-byte Frame)
```
[Byte 0]     Payload Length
[Byte 1]     Sequence Counter (0..255)
[Bytes 2..5] Big-Endian Unix Epoch Timestamp
[Bytes 6..7] Salt / IV
[Byte 8]     Type (8=SOC, 6=Range, 2=Lock, 3=Charging, 7=Time to Charge)
[Bytes 9..N] Data Payload
```

---

## 5. Security & Safety Principles

1. **Physical Safety**: Lock/Unlock commands require an explicit confirmation prompt and a security PIN.
2. **Access Control**: Application binds to `127.0.0.1` by default to prevent unauthorized network access.
3. **Audit Logging**: Every command attempt (Lock, Unlock, Disconnect) is logged to the SQLite database with timestamp, username, and success/failure status.
4. **Non-Destructive Protocol Policy**: Follows strict ethical testing standards—no cryptographic bypass, cracking, or unauthorized command replay is performed. Telemetry is read passively over standard notification channels.

---

## 6. Running Tests

```bash
# Windows
.\venv\Scripts\python -m unittest discover tests

# Linux / Raspberry Pi
./venv/bin/python -m unittest discover tests
```
