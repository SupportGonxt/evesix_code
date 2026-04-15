#!/bin/bash
# Setup script for robot dashboard logging
# Run this once on your Raspberry Pi to configure persistent logging

set -e

echo "========================================="
echo "Robot Dashboard Logging Setup"
echo "========================================="
echo

# Get the current directory (where the script is located)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
DASHBOARD_PATH="$SCRIPT_DIR/dashboard.py"

# Check if dashboard.py exists
if [ ! -f "$DASHBOARD_PATH" ]; then
    echo "Error: dashboard.py not found at $DASHBOARD_PATH"
    exit 1
fi

echo "1. Creating log directory..."
sudo mkdir -p /var/log/robot
sudo chown $USER:$USER /var/log/robot
echo "   ✓ Log directory created: /var/log/robot (owned by $USER)"
echo

echo "2. Installing systemd service..."
# Update the service file with the correct path and user
sed -e "s|/home/pi/robot|$SCRIPT_DIR|g" \
    -e "s|User=pi|User=$USER|g" \
    "$SCRIPT_DIR/robot.service" | \
    sudo tee /etc/systemd/system/robot.service > /dev/null
echo "   ✓ Service file installed (running as $USER)"
echo

echo "3. Installing logrotate configuration..."
sudo cp "$SCRIPT_DIR/robot.logrotate" /etc/logrotate.d/robot
echo "   ✓ Logrotate configured (7 days rotation)"
echo

echo "4. Making log viewer executable..."
chmod +x "$SCRIPT_DIR/log_viewer.py"
echo "   ✓ Log viewer ready"
echo

echo "5. Reloading systemd..."
sudo systemctl daemon-reload
echo "   ✓ Systemd reloaded"
echo

echo "Setup complete!"
echo
echo "Next steps:"
echo "========================================="
echo
echo "Start the service:"
echo "  sudo systemctl start robot.service"
echo
echo "Enable auto-start on boot:"
echo "  sudo systemctl enable robot.service"
echo
echo "Check service status:"
echo "  sudo systemctl status robot.service"
echo
echo "View live logs:"
echo "  python3 log_viewer.py -f"
echo
echo "View last 200 lines:"
echo "  python3 log_viewer.py -n 200"
echo
echo "View recent errors:"
echo "  python3 log_viewer.py --errors"
echo
echo "Manual log access:"
echo "  tail -f /var/log/robot/robot.log"
echo
echo "========================================="
