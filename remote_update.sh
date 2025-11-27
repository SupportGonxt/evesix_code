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

# Kill any running processes from old location immediately
log "Stopping any running processes from old installation..."
pkill -9 -f "/home/gonxt/kivy/dashboard.py" 2>/dev/null || true
pkill -9 -f "/home/gonxt/kivy/cloudSync.py" 2>/dev/null || true
sudo pkill -9 -f "/home/gonxt/kivy/dashboard.py" 2>/dev/null || true
sudo pkill -9 -f "/home/gonxt/kivy/cloudSync.py" 2>/dev/null || true
log "Old processes stopped"

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

# Check if git is installed
if ! command -v git &> /dev/null; then
    log "ERROR: git is not installed. Please install git first: sudo apt-get install git"
    exit 1
fi

# Handle migration vs update
if [ "$MIGRATION_MODE" = true ]; then
    log "Performing migration to new location..."
    
    # Clone fresh repository to new location
    log "Cloning repository to $NEW_REPO_DIR"
    if ! git clone "$REPO_URL" "$NEW_REPO_DIR"; then
        log "ERROR: Failed to clone repository"
        exit 1
    fi
    
    log "Migration completed successfully"
else
    log "Performing update in existing location..."
    
    # Fix ownership FIRST before git operations
    log "Fixing ownership and permissions..."
    sudo chown -R gonxt:gonxt "$NEW_REPO_DIR"
    log "Ownership set to gonxt:gonxt"
    
    # Update existing repository
    cd "$NEW_REPO_DIR"
    
    # Verify this is a git repository
    if [ ! -d ".git" ]; then
        log "ERROR: $NEW_REPO_DIR is not a git repository"
        exit 1
    fi
    
    # Add as safe directory for git (both for root and gonxt user)
    git config --global --add safe.directory "$NEW_REPO_DIR" 2>/dev/null || true
    sudo -u gonxt git config --global --add safe.directory "$NEW_REPO_DIR" 2>/dev/null || true
    
    # Stash any local changes (run as gonxt user)
    log "Stashing local changes..."
    sudo -u gonxt git stash || log "WARNING: Git stash failed, continuing..."
    
    # Pull latest changes with error handling (run as gonxt user)
    log "Pulling latest code..."
    if ! sudo -u gonxt git pull origin main; then
        log "ERROR: Git pull failed. There may be merge conflicts."
        log "Manual intervention required. Check the repository state."
        exit 1
    fi
    
    log "Update completed successfully"
fi

# Ensure ownership is correct after all operations
log "Ensuring correct ownership..."
sudo chown -R gonxt:gonxt "$NEW_REPO_DIR"
sudo chmod +x "$NEW_REPO_DIR/$VENV_DIR/bin/activate" 2>/dev/null || true
log "Ownership set to gonxt:gonxt"

# Verify virtual environment exists
cd "$NEW_REPO_DIR"
if [ ! -d "$VENV_DIR" ]; then
    log "ERROR: Virtual environment not found at $NEW_REPO_DIR/$VENV_DIR"
    exit 1
fi
log "Virtual environment verified at $NEW_REPO_DIR/$VENV_DIR"

# Create startup script
log "Creating startup script..."

# Create with proper permissions (use sudo for writing to /home/gonxt)
STARTUP_SCRIPT="/home/gonxt/startup.sh"
sudo bash -c "cat > $STARTUP_SCRIPT" << 'EOF' || { log "ERROR: Cannot write to $STARTUP_SCRIPT"; exit 1; }
#!/bin/bash

# Wait for system to be ready
sleep 5

# Change to evesix_code directory
cd /home/gonxt/evesix_code

# Verify virtual environment exists
if [ ! -f "shatyenv/bin/activate" ]; then
    echo "ERROR: Virtual environment not found" >> /home/gonxt/startup_error.log
    exit 1
fi

# Activate virtual environment
source /home/gonxt/evesix_code/shatyenv/bin/activate

# Launch dashboard and cloudSync in background
python3 /home/gonxt/evesix_code/dashboard.py &
python3 /home/gonxt/evesix_code/cloudSync.py &

EOF

sudo chmod +x "$STARTUP_SCRIPT" || { log "ERROR: Cannot set execute permission on $STARTUP_SCRIPT"; exit 1; }
log "Startup script created at $STARTUP_SCRIPT with improved error handling"

# Disable old startup script if it exists
if [ -f "/home/gonxt/kivy/startup.sh" ]; then
    log "Disabling old startup script..."
    sudo mv /home/gonxt/kivy/startup.sh /home/gonxt/kivy/startup.sh.disabled 2>/dev/null || true
    log "Old startup script disabled"
fi

# Update .bashrc to use new dashboard path
log "Updating .bashrc..."
# Replace old kivy path with new evesix_code path using sed substitution
sed -i 's|python3 /home/gonxt/kivy/dashboard\.py|python3 /home/gonxt/evesix_code/dashboard.py|g' /home/gonxt/.bashrc 2>/dev/null || true
sed -i 's|python3 /home/gonxt/kivy/cloudSync\.py|python3 /home/gonxt/evesix_code/cloudSync.py|g' /home/gonxt/.bashrc 2>/dev/null || true
# Also remove any # Launch Dashboard comments
sed -i '/# Launch Dashboard/d' /home/gonxt/.bashrc 2>/dev/null || true
log ".bashrc updated to use new evesix_code path"

# Update crontab for auto-start (use sudo crontab for root)
log "Updating root crontab..."

# Remove old kivy startup entries from both root and user crontabs
log "Removing old crontab entries from all users..."
sudo crontab -l 2>/dev/null | grep -v "/home/gonxt/kivy" | sudo crontab - 2>/dev/null || true
crontab -l 2>/dev/null | grep -v "/home/gonxt/kivy" | crontab - 2>/dev/null || true
log "Old crontab entries removed"

# Check if new entry already exists to prevent duplicates
if sudo crontab -l 2>/dev/null | grep -q "@reboot /home/gonxt/startup.sh"; then
    log "Startup entry already exists in crontab"
else
    # Add startup.sh to root crontab
    (sudo crontab -l 2>/dev/null; echo "@reboot /home/gonxt/startup.sh") | sudo crontab -
    if [ $? -eq 0 ]; then
        log "Added startup.sh to root crontab"
    else
        log "WARNING: Failed to add startup.sh to root crontab"
    fi
fi

log "Crontab updated successfully"

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

# Kill old processes running from /home/gonxt/kivy (both root and user processes)
log "Stopping old processes from previous installation..."
pkill -f "/home/gonxt/kivy/dashboard.py" 2>/dev/null || log "No old dashboard process found"
pkill -f "/home/gonxt/kivy/cloudSync.py" 2>/dev/null || log "No old cloudSync process found"
sudo pkill -f "/home/gonxt/kivy/dashboard.py" 2>/dev/null || true
sudo pkill -f "/home/gonxt/kivy/cloudSync.py" 2>/dev/null || true

log "=== Update Complete ==="
log "Log file saved to: $LOG_FILE"
log ""
echo ""
echo "========================================="
echo "Update completed successfully!"
echo "Log saved to: $LOG_FILE"
echo ""
echo "IMPORTANT NEXT STEPS:"
echo "1. Reboot the robot: sudo reboot"
echo "2. Dashboard will auto-start from /home/gonxt/evesix_code"
echo ""
echo "========================================="
