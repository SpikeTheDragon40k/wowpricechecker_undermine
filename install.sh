#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== Installing underbot systemd units ==="

sudo cp "$SCRIPT_DIR/price-alert.service" /etc/systemd/system/price-alert.service
sudo cp "$SCRIPT_DIR/price-alert.timer" /etc/systemd/system/price-alert.timer
sudo cp "$SCRIPT_DIR/credits-checker.service" /etc/systemd/system/credits-checker.service
sudo cp "$SCRIPT_DIR/credits-checker.timer" /etc/systemd/system/credits-checker.timer

echo "=== Reloading systemd ==="
sudo systemctl daemon-reload

echo "=== Enabling and starting timers ==="
sudo systemctl enable price-alert.timer
sudo systemctl start price-alert.timer
sudo systemctl enable credits-checker.timer
sudo systemctl start credits-checker.timer

echo "=== Status ==="
systemctl status price-alert.timer credits-checker.timer --no-pager

echo ""
echo "Done. price-alert runs at 00:00, 08:00, 16:00 daily."
echo "credits-checker runs every 2 hours."
echo "To test immediately: sudo systemctl start price-alert.service"
