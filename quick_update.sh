#!/bin/bash

# Quick Update Wrapper Script
# Downloads and executes the main update script with cache busting

set -e

echo "=== Robot Remote Update ==="
echo "Downloading update script..."

# Download with cache busting timestamp to /tmp
TIMESTAMP=$(date +%s)
curl -fsSL "https://raw.githubusercontent.com/SupportGonxt/evesix_code/main/remote_update.sh?t=$TIMESTAMP" -o /tmp/remote_update_$TIMESTAMP.sh

# Make executable
chmod +x /tmp/remote_update_$TIMESTAMP.sh

# Execute
echo "Running update script..."
bash /tmp/remote_update_$TIMESTAMP.sh

# Cleanup
rm -f /tmp/remote_update_$TIMESTAMP.sh
