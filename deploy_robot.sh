#!/usr/bin/env bash
# deploy_robot.sh - One-command setup/migration for robot code from Git repo
#
# Usage examples:
#   bash deploy_robot.sh                      # default: systemd service install
#   bash deploy_robot.sh --cron               # use cron instead of systemd
#   bash deploy_robot.sh --branch main        # custom branch
#   bash deploy_robot.sh --repo https://github.com/SupportGonxt/evesix_code.git
#   bash deploy_robot.sh --user gonxt --dir /home/gonxt/apps/evesix_code
#   bash deploy_robot.sh --no-kill            # do not kill existing python processes
#   bash deploy_robot.sh --force              # force reclone (delete existing dir)
#
# Idempotency: Safe to re-run; will update repo & ensure service/cron configured.
# Designed for Raspberry Pi environment.

set -euo pipefail
IFS=$'\n\t'

###############################################################################
# Defaults (can be overridden by flags)
###############################################################################
REPO_URL="https://github.com/SupportGonxt/evesix_code.git"
BRANCH="Error-handling-update-branch"
TARGET_USER="gonxt"
BASE_DIR="/home/${TARGET_USER}/apps"
APP_DIR="${BASE_DIR}/evesix_code"
SERVICE_NAME="robot-dashboard"
USE_CRON="false"
FORCE_RECLONE="false"
KILL_EXISTING="true"
PYTHON_BIN="python3"
VENV_DIR="${APP_DIR}/.venv"
LOG_DIR="${APP_DIR}/logs"
REQUIREMENTS_FILE="requirements.txt"
CRON_LINE="@reboot sleep 15; /bin/bash -c \"cd ${APP_DIR} && source ${VENV_DIR}/bin/activate && /usr/bin/python3 dashboard.py\" >> ${LOG_DIR}/dashboard.log 2>&1"

###############################################################################
print_header() { echo -e "\n===== $* =====\n"; }
err() { echo "[ERROR] $*" >&2; }
info() { echo "[INFO] $*"; }
###############################################################################
usage() {
  grep '^#' "$0" | sed 's/^# //' | head -n 20
  exit 0
}
###############################################################################
# Parse flags
###############################################################################
while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo) REPO_URL="$2"; shift 2;;
    --branch) BRANCH="$2"; shift 2;;
    --user) TARGET_USER="$2"; BASE_DIR="/home/${TARGET_USER}/apps"; APP_DIR="${BASE_DIR}/evesix_code"; shift 2;;
    --dir) APP_DIR="$2"; shift 2;;
    --cron) USE_CRON="true"; shift;;
    --force) FORCE_RECLONE="true"; shift;;
    --no-kill) KILL_EXISTING="false"; shift;;
    --help|-h) usage;;
    *) err "Unknown argument: $1"; usage;;
  esac
done
VENV_DIR="${APP_DIR}/.venv"
LOG_DIR="${APP_DIR}/logs"
CRON_LINE="@reboot sleep 15; /bin/bash -c \"cd ${APP_DIR} && source ${VENV_DIR}/bin/activate && /usr/bin/python3 dashboard.py\" >> ${LOG_DIR}/dashboard.log 2>&1"

###############################################################################
# Pre-flight checks
###############################################################################
print_header "Pre-flight"
if [[ $(id -u) -eq 0 ]]; then
  info "Running as root. Will adjust file ownership to ${TARGET_USER} where needed."
else
  if [[ "$(whoami)" != "${TARGET_USER}" ]]; then
    err "Run as ${TARGET_USER} or root (to set ownership)."; exit 1
  fi
fi
command -v git >/dev/null || { err "git not installed"; exit 1; }
command -v ${PYTHON_BIN} >/dev/null || { err "python3 not installed"; exit 1; }

###############################################################################
# (1) Kill existing processes if requested
###############################################################################
print_header "Process cleanup"
if [[ "${KILL_EXISTING}" == "true" ]]; then
  EXISTING=$(pgrep -af python || true)
  if [[ -n "${EXISTING}" ]]; then
    info "Existing python processes:"; echo "${EXISTING}" | sed 's/^/  /'
    info "Killing old dashboard/pageOne processes"
    pkill -f dashboard.py || true
    pkill -f pageOne.py || true
  else
    info "No existing python processes found."
  fi
else
  info "Skipping process kill (--no-kill)."
fi

###############################################################################
# (2) Prepare directories
###############################################################################
print_header "Directory setup"
mkdir -p "${BASE_DIR}" || true
if [[ -d "${APP_DIR}" && "${FORCE_RECLONE}" == "true" ]]; then
  info "Force reclone enabled: removing existing ${APP_DIR}"
  rm -rf "${APP_DIR}"
fi

###############################################################################
# (3) Clone or update repo
###############################################################################
print_header "Git clone/update"
if [[ ! -d "${APP_DIR}" ]]; then
  info "Cloning ${REPO_URL} into ${APP_DIR}";
  git clone "${REPO_URL}" "${APP_DIR}"
else
  info "Repo exists. Updating.";
  cd "${APP_DIR}"
  git fetch --all --prune
  git reset --hard origin/${BRANCH} || git checkout ${BRANCH}
fi
cd "${APP_DIR}"
info "Checking out branch ${BRANCH}";
if git rev-parse --verify "${BRANCH}" >/dev/null 2>&1; then
  git checkout "${BRANCH}"
else
  err "Branch ${BRANCH} not found"; exit 1
fi

###############################################################################
# Adjust ownership (if root)
###############################################################################
if [[ $(id -u) -eq 0 ]]; then
  chown -R "${TARGET_USER}:${TARGET_USER}" "${APP_DIR}"
fi

###############################################################################
# (4) Python virtual environment
###############################################################################
print_header "Virtual environment"
if [[ ! -d "${VENV_DIR}" ]]; then
  info "Creating venv at ${VENV_DIR}";
  ${PYTHON_BIN} -m venv "${VENV_DIR}"
fi
source "${VENV_DIR}/bin/activate"
python -m pip install --upgrade pip wheel

###############################################################################
# (5) Install requirements
###############################################################################
print_header "Python dependencies"
if [[ -f "${REQUIREMENTS_FILE}" ]]; then
  pip install -r "${REQUIREMENTS_FILE}" || { err "Failed to install requirements"; exit 1; }
else
  err "Missing requirements.txt"; exit 1
fi

###############################################################################
# (6) Logs directory
###############################################################################
print_header "Logs directory"
mkdir -p "${LOG_DIR}"

###############################################################################
# (7) Setup systemd OR cron
###############################################################################
if [[ "${USE_CRON}" == "false" ]]; then
  print_header "Systemd service setup"
  SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
  if [[ $(id -u) -ne 0 ]]; then
    err "Systemd setup requires root. Re-run with sudo or use --cron."; exit 1
  fi
  cat > "${SERVICE_FILE}" <<EOF
[Unit]
Description=Robot Dashboard Service
After=network.target mariadb.service

[Service]
Type=simple
WorkingDirectory=${APP_DIR}
ExecStart=/bin/bash -c 'source ${VENV_DIR}/bin/activate && /usr/bin/python3 dashboard.py'
Restart=on-failure
User=${TARGET_USER}
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF
  systemctl daemon-reload
  systemctl enable "${SERVICE_NAME}.service"
  systemctl restart "${SERVICE_NAME}.service"
  systemctl status "${SERVICE_NAME}.service" --no-pager || true
else
  print_header "Cron setup"
  if [[ $(id -u) -ne 0 ]]; then
    err "Cron (root) requires sudo. Re-run with sudo or modify user crontab manually."; exit 1
  fi
  # Remove old flash-drive lines
  TMP_CRON=$(mktemp)
  sudo crontab -l 2>/dev/null | grep -v '/media/usb' | grep -v 'dashboard.py' | grep -v 'LocalStor.py' > "${TMP_CRON}" || true
  echo "${CRON_LINE}" >> "${TMP_CRON}"
  sudo crontab "${TMP_CRON}"
  rm -f "${TMP_CRON}" || true
  info "New root crontab:"; sudo crontab -l
fi

###############################################################################
# (8) Final summary
###############################################################################
print_header "Summary"
echo "Repo:        ${REPO_URL}" 
echo "Branch:      ${BRANCH}" 
echo "App Dir:     ${APP_DIR}" 
echo "Venv:        ${VENV_DIR}" 
echo "Logs:        ${LOG_DIR}" 
echo "Startup:     $( [[ "${USE_CRON}" == "true" ]] && echo cron || echo systemd:${SERVICE_NAME})"

info "Deployment complete.";
if [[ "${USE_CRON}" == "false" ]]; then
  echo "Check logs: journalctl -u ${SERVICE_NAME} -f"
else
  echo "After reboot, tail log: tail -f ${LOG_DIR}/dashboard.log"
fi

exit 0
