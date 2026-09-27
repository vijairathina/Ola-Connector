/**
 * Dashboard Real-Time Telemetry & Live Updates Controller
 * Uses Server-Sent Events (SSE) for sub-second reactive updates.
 */

let pendingCommand = null;
const CIRCUMFERENCE = 2 * Math.PI * 95; // r=95 -> ~596.9

document.addEventListener("DOMContentLoaded", () => {
  initEventSource();
});

function initEventSource() {
  const evtSource = new EventSource("/api/scooter/events");

  evtSource.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      updateDashboard(data);
    } catch (e) {
      console.error("Error parsing telemetry event:", e);
    }
  };

  evtSource.onerror = (err) => {
    console.warn("SSE connection interrupted. Reconnecting in 3s...", err);
    evtSource.close();
    setTimeout(initEventSource, 3000);
  };
}

function updateDashboard(status) {
  // 1. Connection status
  const topPill = document.getElementById("top-status-pill");
  const topText = document.getElementById("top-status-text");
  const alertBox = document.getElementById("disconnected-alert");
  const simBanner = document.getElementById("sim-banner");

  if (status.is_simulated) {
    if (simBanner) simBanner.style.display = "flex";
  }

  if (status.connected) {
    topPill.className = "status-pill online";
    topText.textContent = "CONNECTED";
    alertBox.style.display = "none";
  } else {
    topPill.className = "status-pill offline";
    topText.textContent = "DISCONNECTED";
    alertBox.style.display = "block";
    if (status.error_message) {
      document.getElementById("disconnected-reason").textContent = status.error_message;
    }
  }

  // 2. Battery & Dial
  const batVal = document.getElementById("battery-val");
  const dial = document.getElementById("battery-dial");
  if (status.battery_percent !== null && status.battery_percent !== undefined) {
    batVal.textContent = `${status.battery_percent}%`;
    const offset = CIRCUMFERENCE - (status.battery_percent / 100) * CIRCUMFERENCE;
    dial.style.strokeDashoffset = offset;

    // Dial color adjustments
    if (status.battery_percent < 20) {
      dial.style.stroke = "var(--accent-rose)";
    } else if (status.battery_percent < 40) {
      dial.style.stroke = "var(--accent-amber)";
    } else {
      dial.style.stroke = "var(--accent-cyan)";
    }
  } else {
    batVal.textContent = "--%";
    dial.style.strokeDashoffset = CIRCUMFERENCE;
  }

  // 3. Estimated Range
  const rangeVal = document.getElementById("range-val");
  rangeVal.textContent = status.estimated_range_km !== null ? status.estimated_range_km : "--";

  // 4. Charging System
  const chargingPill = document.getElementById("charging-indicator-pill");
  const chargingPillText = document.getElementById("charging-pill-text");
  const chargingPlug = document.getElementById("charging-plug-status");
  const chargingTime = document.getElementById("charging-time-val");
  const heroCard = document.getElementById("battery-hero-card");

  if (status.charging === true) {
    chargingPill.className = "status-pill online";
    chargingPillText.textContent = "Charging";
    chargingPlug.innerHTML = "<span style='color: var(--accent-emerald); font-weight: 700;'>⚡ CONNECTED</span>";
    heroCard.classList.add("charging-active");
    if (status.time_to_full_charge_min) {
      const hrs = Math.floor(status.time_to_full_charge_min / 60);
      const mins = status.time_to_full_charge_min % 60;
      chargingTime.textContent = hrs > 0 ? `${hrs}h ${mins}m` : `${mins} min`;
    } else {
      chargingTime.textContent = "Calculating...";
    }
  } else if (status.charging === false) {
    chargingPill.className = "status-pill";
    chargingPillText.textContent = "Discharging";
    chargingPlug.textContent = "Unplugged";
    chargingTime.textContent = "--:--";
    heroCard.classList.remove("charging-active");
  } else {
    chargingPlug.textContent = "Status unavailable";
    chargingTime.textContent = "--:--";
    heroCard.classList.remove("charging-active");
  }

  // 5. Lock & Security
  const lockPill = document.getElementById("lock-status-pill");
  const lockText = document.getElementById("lock-status-text");
  const handleText = document.getElementById("steering-handle-text");
  const btnLock = document.getElementById("btn-lock");
  const btnUnlock = document.getElementById("btn-unlock");

  const lockState = (status.lock_status || "UNKNOWN").toUpperCase();
  lockText.textContent = lockState;
  handleText.textContent = status.steering_status || "--";

  if (lockState === "LOCKED") {
    lockPill.className = "status-pill offline";
    btnLock.disabled = true;
    btnLock.style.opacity = "0.5";
    btnUnlock.disabled = false;
    btnUnlock.style.opacity = "1";
  } else if (lockState === "UNLOCKED") {
    lockPill.className = "status-pill online";
    btnUnlock.disabled = true;
    btnUnlock.style.opacity = "0.5";
    btnLock.disabled = false;
    btnLock.style.opacity = "1";
  } else {
    lockPill.className = "status-pill";
    btnLock.disabled = false;
    btnUnlock.disabled = false;
  }

  // 6. Bluetooth details
  if (status.device_name) document.getElementById("ble-name").textContent = status.device_name;
  if (status.device_address) document.getElementById("ble-mac").textContent = status.device_address;
  if (status.rssi !== null) {
    document.getElementById("ble-rssi").textContent = `${status.rssi} dBm`;
  }
  if (status.last_updated) {
    document.getElementById("ble-last-seen").textContent = status.last_updated.split(" ")[1] || status.last_updated;
  }

  // 7. Telemetry Stats Tiles
  if (status.odometer_km !== null) {
    document.getElementById("stat-odometer").innerHTML = `${status.odometer_km} <span style="font-size: 0.9rem; color: var(--text-muted);">km</span>`;
  }
  if (status.driving_mode) {
    document.getElementById("stat-drive-mode").textContent = status.driving_mode;
  }
  if (status.side_stand !== null) {
    document.getElementById("stat-side-stand").textContent = status.side_stand ? "Deployed (Down)" : "Retracted (Up)";
  }
}

// -----------------------------------------------------------------
// VEHICLE COMMAND CONFIRMATION & PIN MODAL
// -----------------------------------------------------------------
function promptLockCommand() {
  openCommandModal("lock", "Lock Scooter", "Are you sure you want to lock the steering handle and arm vehicle security?");
}

function promptUnlockCommand() {
  openCommandModal("unlock", "Unlock Scooter", "Are you sure you want to unlock the scooter? Please ensure the scooter is safely parked.");
}

function openCommandModal(command, title, description) {
  pendingCommand = command;
  document.getElementById("modal-title").textContent = title;
  document.getElementById("modal-description").textContent = description;
  document.getElementById("modal-pin").value = "";
  
  const confirmBtn = document.getElementById("modal-confirm-btn");
  confirmBtn.onclick = executePendingCommand;
  
  document.getElementById("command-modal").classList.add("active");
  document.getElementById("modal-pin").focus();
}

function closeCommandModal() {
  pendingCommand = null;
  document.getElementById("command-modal").classList.remove("active");
}

async function executePendingCommand() {
  if (!pendingCommand) return;
  const pin = document.getElementById("modal-pin").value.trim();
  const cmd = pendingCommand;
  const confirmBtn = document.getElementById("modal-confirm-btn");

  confirmBtn.disabled = true;
  confirmBtn.textContent = "Sending...";

  try {
    const res = await fetch(`/api/scooter/${cmd}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        confirmed: true,
        pin: pin
      })
    });
    const result = await res.json();
    if (result.success) {
      closeCommandModal();
    } else {
      alert("Command Failed: " + (result.error || "Unknown error"));
    }
  } catch (e) {
    alert("Network or connection error: " + e.message);
  } finally {
    confirmBtn.disabled = false;
    confirmBtn.textContent = "Confirm";
  }
}

// -----------------------------------------------------------------
// BLE SCANNER MODAL
// -----------------------------------------------------------------
function openScanModal() {
  const modal = document.getElementById("scan-modal");
  const loading = document.getElementById("scan-loading");
  const results = document.getElementById("scan-results");

  modal.classList.add("active");
  loading.style.display = "block";
  results.style.display = "none";
  results.innerHTML = "";

  fetch("/api/scooter/scan")
    .then(r => r.json())
    .then(data => {
      loading.style.display = "none";
      results.style.display = "flex";

      if (data.success && data.devices && data.devices.length > 0) {
        data.devices.forEach(dev => {
          const item = document.createElement("div");
          item.className = "stat-tile";
          item.style.cursor = "pointer";
          item.innerHTML = `
            <div>
              <div style="font-weight: 600; font-size: 0.95rem; color: ${dev.is_ola ? 'var(--accent-cyan)' : 'var(--text-primary)'}">
                ${dev.name} ${dev.is_ola ? '⭐ (Ola)' : ''}
              </div>
              <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.8rem; color: var(--text-muted);">${dev.address}</div>
            </div>
            <div style="display: flex; align-items: center; gap: 0.75rem;">
              <span style="font-family: 'JetBrains Mono', monospace; font-size: 0.85rem;">${dev.rssi} dBm</span>
              <button class="btn btn-secondary" style="padding: 0.3rem 0.6rem; font-size: 0.8rem;">Connect</button>
            </div>
          `;
          item.onclick = () => selectAndConnect(dev.address);
          results.appendChild(item);
        });
      } else {
        results.innerHTML = "<div style='padding: 1.5rem; text-align: center; color: var(--text-muted);'>No devices found.</div>";
      }
    })
    .catch(err => {
      loading.style.display = "none";
      results.style.display = "block";
      results.innerHTML = `<div style='color: var(--accent-rose); padding: 1rem;'>Scan failed: ${err.message}</div>`;
    });
}

function closeScanModal() {
  document.getElementById("scan-modal").classList.remove("active");
}

async function selectAndConnect(address) {
  closeScanModal();
  try {
    await fetch("/api/scooter/connect", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ address: address })
    });
  } catch (e) {
    alert("Connection request failed: " + e.message);
  }
}

function manualConnect() {
  fetch("/api/scooter/connect", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({})
  });
}

function toggleSimCharging() {
  fetch("/api/scooter/simulation/toggle_charging", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({})
  });
}

// -----------------------------------------------------------------
// WEB BLUETOOTH (MOBILE PHONE DIRECT BLE CONNECTION)
// -----------------------------------------------------------------
let webBleDevice = null;
let webBleChar = null;

async function connectViaWebBluetooth() {
  // 1. Check if running inside our Native Android Companion APK
  if (window.AndroidScooter && typeof window.AndroidScooter.connectScooter === "function") {
    console.log("Triggering Native Android BLE connection via APK bridge...");
    const topStatus = document.getElementById("top-status-pill");
    if (topStatus) {
      topStatus.className = "status-pill offline";
      topStatus.innerHTML = '<span class="status-dot"></span><span>Connecting BLE...</span>';
    }
    window.AndroidScooter.connectScooter("87:1A:44:60:00:28");
    return;
  }

  // 2. Otherwise fallback to Chrome Web Bluetooth
  if (!navigator.bluetooth) {
    alert("Web Bluetooth is not supported on this browser.\nPlease open this dashboard in Google Chrome on your Android phone.");
    return;
  }

  const OLA_SERVICE_UUID = "6e400001-b5a3-f393-e0a9-871a44600028";
  const OLA_RX_CHAR_UUID = "6e400002-b5a3-f393-e0a9-e50e24dcca9e";

  try {
    console.log("Requesting Web Bluetooth device...");
    webBleDevice = await navigator.bluetooth.requestDevice({
      filters: [
        { namePrefix: "OLA" }
      ],
      optionalServices: [
        OLA_SERVICE_UUID,
        "00001800-0000-1000-8000-00805f9b34fb",
        "00001801-0000-1000-8000-00805f9b34fb"
      ]
    });

    console.log("Selected device:", webBleDevice.name);
    webBleDevice.addEventListener("gattserverdisconnected", onWebBleDisconnected);

    const server = await webBleDevice.gatt.connect();
    console.log("Connected to GATT Server.");

    const service = await server.getPrimaryService(OLA_SERVICE_UUID);
    webBleChar = await service.getCharacteristic(OLA_RX_CHAR_UUID);

    await webBleChar.startNotifications();
    webBleChar.addEventListener("characteristicvaluechanged", handleWebBleNotification);
    console.log("Subscribed to Ola RX telemetry notifications via Phone Bluetooth!");

    // Update status indicator
    const topStatus = document.getElementById("top-status-pill");
    if (topStatus) {
      topStatus.className = "status-pill online";
      topStatus.innerHTML = '<span class="status-dot"></span><span>Phone BLE: ' + webBleDevice.name + '</span>';
    }
    const alertBanner = document.getElementById("disconnected-alert");
    if (alertBanner) alertBanner.style.display = "none";

  } catch (err) {
    console.error("Web Bluetooth error:", err);
    if (err.name !== "NotFoundError") {
      alert("Bluetooth connection failed: " + err.message);
    }
  }
}

function handleWebBleNotification(event) {
  const value = event.target.value;
  const uint8 = new Uint8Array(value.buffer, value.byteOffset, value.byteLength);
  const hex = Array.from(uint8).map(b => b.toString(16).padStart(2, '0')).join('');

  // Send packet to local backend so server state and SQLite database stay in sync
  fetch("/api/scooter/feed_packet", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      hex: hex,
      name: webBleDevice ? webBleDevice.name : "OLAS1",
      address: "87:1A:44:60:00:28"
    })
  }).catch(e => console.debug("Feed packet network err:", e));
}

function onWebBleDisconnected() {
  console.warn("Web Bluetooth device disconnected.");
  const topStatus = document.getElementById("top-status-pill");
  if (topStatus) {
    topStatus.className = "status-pill offline";
    topStatus.innerHTML = '<span class="status-dot"></span><span>Disconnected</span>';
  }
  const alertBanner = document.getElementById("disconnected-alert");
  if (alertBanner) alertBanner.style.display = "block";
}

// Global functions invoked from Android Native WebView Bridge
window.onNativeBleState = function(connected, deviceName) {
  console.log("Native BLE connection status:", connected, deviceName);
  const topStatus = document.getElementById("top-status-pill");
  if (topStatus) {
    topStatus.className = connected ? "status-pill online" : "status-pill offline";
    topStatus.innerHTML = '<span class="status-dot"></span><span>' + (connected ? ('Phone BLE: ' + (deviceName || 'OLAS1')) : 'Disconnected') + '</span>';
  }
  const alertBanner = document.getElementById("disconnected-alert");
  if (alertBanner) alertBanner.style.display = connected ? "none" : "block";
};

window.feedRawPacket = function(hex) {
  fetch("/api/scooter/feed_packet", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      hex: hex,
      name: "OLAS1 (Phone BLE)",
      address: "87:1A:44:60:00:28"
    })
  }).catch(e => console.debug("Feed packet err:", e));
};


