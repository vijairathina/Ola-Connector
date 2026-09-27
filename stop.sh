#!/usr/bin/env bash
# Stop Ola Scooter Web Service

if [ -f "/etc/systemd/system/ola-scooter-web.service" ]; then
    echo "Stopping ola-scooter-web service..."
    sudo systemctl stop ola-scooter-web
    echo "Service stopped."
else
    echo "Killing any running python run.py process..."
    pkill -f "python run.py" || echo "No process found."
fi
