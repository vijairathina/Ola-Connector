#!/usr/bin/env bash
# Check Ola Scooter Web Service Status

echo "=== Systemd Service Status ==="
if [ -f "/etc/systemd/system/ola-scooter-web.service" ]; then
    sudo systemctl status ola-scooter-web --no-pager
else
    echo "Systemd service not installed yet. Run ./install.sh first."
fi

echo ""
echo "=== Recent Journal Logs ==="
if command -v journalctl &> /dev/null; then
    sudo journalctl -u ola-scooter-web -n 25 --no-pager
fi
