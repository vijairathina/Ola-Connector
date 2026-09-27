#!/usr/bin/env bash
# Start Ola Scooter Web Service

if systemctl is-active --quiet ola-scooter-web 2>/dev/null; then
    echo "ola-scooter-web service is already running."
elif [ -f "/etc/systemd/system/ola-scooter-web.service" ]; then
    echo "Starting ola-scooter-web systemd service..."
    sudo systemctl start ola-scooter-web
    sudo systemctl status ola-scooter-web --no-pager
else
    echo "Starting in foreground mode via venv..."
    PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    cd "$PROJECT_DIR"
    ./venv/bin/python run.py "$@"
fi
