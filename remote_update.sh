#!/bin/bash

# Remote Robot Update Script
# This script handles automatic code updates for robots via Raspi Connect
# Supports migration from old location (/home/gonxt/kivy) to new location (/home/gonxt/evesix_code)

set -e  # Exit on error

# Configuration
OLD_REPO_DIR="/home/gonxt/kivy"
NEW_REPO_DIR="/home/gonxt/evesix_code"
REPO_URL="https://github.com/SupportGonxt/evesix_code.git"
BACKUP_DIR="/home/gonxt/backups"
VENV_DIR="shatyenv"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Initialize log file
LOG_FILE="/home/gonxt/update_log_$(date +%Y%m%d_%H%M%S).txt"
log "=== Robot Update Script Started ==="

# Detect which directory exists
MIGRATION_MODE=false
CURRENT_DIR=""

log "Checking directory structure..."
if [ -d "$OLD_REPO_DIR" ] && [ ! -d "$NEW_REPO_DIR" ]; then
    log "Old repository detected at $OLD_REPO_DIR - Migration mode enabled"
    MIGRATION_MODE=true
    CURRENT_DIR="$OLD_REPO_DIR"
elif [ -d "$NEW_REPO_DIR" ]; then
    log "New repository detected at $NEW_REPO_DIR - Update mode"
    CURRENT_DIR="$NEW_REPO_DIR"
else
    log "ERROR: No repository found at old or new location"
    log "Creating new installation at $NEW_REPO_DIR"
    MIGRATION_MODE=true
    CURRENT_DIR=""
fi

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Backup existing code if it exists
if [ -n "$CURRENT_DIR" ] && [ -d "$CURRENT_DIR" ]; then
    BACKUP_NAME="backup_$(date +%Y%m%d_%H%M%S)"
    log "Creating backup: $BACKUP_DIR/$BACKUP_NAME"
    cp -r "$CURRENT_DIR" "$BACKUP_DIR/$BACKUP_NAME"
    log "Backup created successfully"
fi

# Handle migration vs update
if [ "$MIGRATION_MODE" = true ]; then
    log "Performing migration to new location..."
    
    # Clone fresh repository to new location
    log "Cloning repository to $NEW_REPO_DIR"
    git clone "$REPO_URL" "$NEW_REPO_DIR"
    
    log "Migration completed successfully"
else
    log "Performing update in existing location..."
    
    # Update existing repository
    cd "$NEW_REPO_DIR"
    
    # Stash any local changes
    log "Stashing local changes..."
    git stash
    
    # Pull latest changes
    log "Pulling latest code..."
    git pull origin main
    
    log "Update completed successfully"
fi

# Verify virtual environment exists
cd "$NEW_REPO_DIR"
if [ ! -d "$VENV_DIR" ]; then
    log "ERROR: Virtual environment not found at $NEW_REPO_DIR/$VENV_DIR"
    exit 1
fi
log "Virtual environment verified at $NEW_REPO_DIR/$VENV_DIR"

# Create startup script
log "Creating startup script..."

# Create with proper permissions
STARTUP_SCRIPT="/home/gonxt/startup.sh"
cat > "$STARTUP_SCRIPT" << 'EOF' || { log "ERROR: Cannot write to $STARTUP_SCRIPT - try running with sudo"; exit 1; }
#!/bin/bash

# Wait for network
sleep 5

# Determine which network interface is active
if nmcli device status | grep -q "usb0.*connected"; then
    echo "Modem network detected (usb0)"
elif nmcli device status | grep -q "wlan0.*connected"; then
    echo "WiFi network detected (wlan0)"
else
    echo "No network connection detected"
fi

# Kill any existing dashboard processes
pkill -f "python.*dashboard.py" || true

# Change to repository directory
cd /home/gonxt/evesix_code

# Activate virtual environment
source shatyenv/bin/activate

# Start dashboard
python3 dashboard.py &

echo "Dashboard started"
EOF

chmod +x "$STARTUP_SCRIPT" || { log "ERROR: Cannot set execute permission on $STARTUP_SCRIPT"; exit 1; }
log "Startup script created at $STARTUP_SCRIPT"

# Clean up .bashrc from old dashboard entries
log "Cleaning up .bashrc..."
# Remove any lines containing dashboard.py to ensure clean state
sed -i '/dashboard\.py/d' ~/.bashrc
log ".bashrc cleaned - removed all dashboard.py references"

# Update crontab for auto-start
log "Updating crontab..."
# Remove old entries
crontab -l 2>/dev/null | grep -v "startup.sh" | grep -v "cloudSync.py" | crontab - || true

# Add new entries
(crontab -l 2>/dev/null; echo "@reboot /home/gonxt/startup.sh") | crontab -
if [ $? -ne 0 ]; then
    log "ERROR: Failed to add startup.sh to crontab"
else
    log "Added startup.sh to crontab"
fi

(crontab -l 2>/dev/null; echo "@reboot sleep 120 && cd /home/gonxt/evesix_code && /home/gonxt/evesix_code/shatyenv/bin/python3 /home/gonxt/evesix_code/cloudSync.py") | crontab -
if [ $? -ne 0 ]; then
    log "ERROR: Failed to add cloudSync.py to crontab"
else
    log "Added cloudSync.py to crontab"
fi

log "Crontab updated successfully"

# Verify crontab entries
log "Verifying crontab entries:"
crontab -l 2>/dev/null | tee -a "$LOG_FILE"

# Test basic imports
log "Testing Python environment..."
cd "$NEW_REPO_DIR"
source "$VENV_DIR/bin/activate"

python3 -c "import kivy; print('Kivy import: OK')" || log "WARNING: Kivy import failed"
python3 -c "import mysql.connector; print('MySQL import: OK')" || log "WARNING: MySQL import failed"

# Verify critical files exist
log "Verifying critical files..."
for file in dashboard.py pageOne.py cloudSync.py; do
    if [ -f "$file" ]; then
        log "✓ $file exists"
    else
        log "✗ WARNING: $file not found"
    fi
done

# Ensure startup script has execute permissions
chmod +x /home/gonxt/startup.sh 2>/dev/null || true

log "=== Update Complete ==="
log "Log file saved to: $LOG_FILE"
log ""
echo ""
echo "========================================="
echo "Update completed successfully!"
echo "Log saved to: $LOG_FILE"
echo ""
echo "Review the log above for any warnings."
echo ""
echo "========================================="
echo "Rebooting in 5 seconds..."
echo "Press Ctrl+C to cancel reboot."
echo "========================================="
sleep 5
log "Rebooting system..."
sudo reboot
