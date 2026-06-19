#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== Installing underbot systemd units ==="

sudo cp "$SCRIPT_DIR/price-alert.service" /etc/systemd/system/price-alert.service
sudo cp "$SCRIPT_DIR/price-alert.timer" /etc/systemd/system/price-alert.timer

echo "=== Reloading systemd ==="
sudo systemctl daemon-reload

echo "=== Enabling and starting timer ==="
sudo systemctl enable price-alert.timer
sudo systemctl start price-alert.timer

echo "=== Status ==="
systemctl status price-alert.timer --no-pager

echo ""
echo "Done. The service will run at 00:00, 08:00, 16:00 daily."
echo "To test immediately: sudo systemctl start price-alert.service"
