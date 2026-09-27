#!/usr/bin/env bash
# ============================================================
# Ola Scooter Bluetooth Web Controller - Raspberry Pi Installer
# Supports Raspberry Pi 3, 4, 5 (Debian / Raspberry Pi OS)
# ============================================================

set -e

echo "=== Installing Dependencies for Ola Scooter Web Controller ==="

# Update package lists and install system Bluetooth and Python libraries
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-venv bluetooth bluez libbluetooth-dev

# Ensure bluetooth service is active
sudo systemctl enable bluetooth
sudo systemctl start bluetooth

# Set working directory to project root
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

# Create virtual environment if not present
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate and install requirements
echo "Installing Python dependencies..."
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt

# Configure systemd service
SERVICE_PATH="/etc/systemd/system/ola-scooter-web.service"
echo "Configuring systemd service at $SERVICE_PATH..."

CURRENT_USER="$(whoami)"

sudo tee "$SERVICE_PATH" > /dev/null <<EOF
[Unit]
Description=Ola Scooter Bluetooth Web Controller
After=network.target bluetooth.target
Wants=bluetooth.target

[Service]
Type=simple
User=$CURRENT_USER
WorkingDirectory=$PROJECT_DIR
ExecStart=$PROJECT_DIR/venv/bin/python $PROJECT_DIR/run.py
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable ola-scooter-web

echo ""
echo "=== Installation Complete! ==="
echo "To start the service:"
echo "  sudo systemctl start ola-scooter-web"
echo "Or use helper scripts:"
echo "  ./start.sh"
echo "  ./status.sh"
echo "  ./stop.sh"
