#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== Installing underbot systemd units ==="

sudo cp "$SCRIPT_DIR/price-alert.service" /etc/systemd/system/price-alert.service
sudo cp "$SCRIPT_DIR/price-alert.timer" /etc/systemd/system/price-alert.timer
sudo cp "$SCRIPT_DIR/credits-checker.service" /etc/systemd/system/credits-checker.service
sudo cp "$SCRIPT_DIR/credits-checker.timer" /etc/systemd/system/credits-checker.timer
sudo cp "$SCRIPT_DIR/underbot-bot.service" /etc/systemd/system/underbot-bot.service

echo "=== Reloading systemd ==="
sudo systemctl daemon-reload

echo "=== Enabling and starting price-alert timer (scans at 00:00, 08:00, 16:00) ==="
sudo systemctl enable price-alert.timer
sudo systemctl start price-alert.timer

echo "=== Enabling and starting credits-checker timer (every 2 hours) ==="
sudo systemctl enable credits-checker.timer
sudo systemctl start credits-checker.timer

echo "=== Enabling and starting bot daemon (interactive commands) ==="
sudo systemctl enable underbot-bot.service
sudo systemctl start underbot-bot.service

echo "=== Status ==="
systemctl status price-alert.timer credits-checker.timer underbot-bot.service --no-pager

echo ""
echo "Done."
echo "  price-alert     runs at 00:00, 08:00, 16:00 daily."
echo "  credits-checker runs every 2 hours."
echo "  underbot-bot    runs continuously for interactive commands."
echo ""
echo "To test scanner:   sudo systemctl start price-alert.service"
echo "To check bot logs: sudo journalctl -u underbot-bot.service -f"
