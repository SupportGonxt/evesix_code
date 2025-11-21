#!/bin/bash

# Quick Update Wrapper Script
# Downloads and executes the main update script with cache busting

echo "Downloading update script..."

# Download with cache busting timestamp
curl -fsSL "https://raw.githubusercontent.com/SupportGonxt/evesix_code/main/remote_update.sh?t=$(date +%s)" -o /tmp/remote_update.sh

# Make executable
chmod +x /tmp/remote_update.sh

# Execute
echo "Running update script..."
bash /tmp/remote_update.sh
