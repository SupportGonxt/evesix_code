#!/usr/bin/env bash
# run_master_sync.sh - cron entry point for the daily D1 -> local reference
# data sync (Master.py). Not used by the Settings screen's manual "sync"
# button (pages.py) - that calls Master.py directly, unaffected by this
# guard, so operators can still force a sync on demand.
#
# Adds two things a bare `python3 Master.py` cron line wouldn't have:
#   1. A flock-based lock so an overlapping invocation (e.g. cron fires
#      while a previous run is still retrying against a flaky connection)
#      can't run concurrently and race on the same sqlite file.
#   2. A once-per-calendar-day guard so re-running deploy_robot.sh (which
#      reinstalls this same cron line, idempotently) or a stray duplicate
#      cron trigger doesn't sync twice in one day.
#
# Master.py already tolerates being offline on its own: cf_d1.py times
# out and retries per request, and Master.py catches D1Error per table
# and still exits 0, so a robot with no network on a given day just logs
# the failure here and tries again at tomorrow's run - nothing below
# needs to special-case that. This script always exits 0 so a flaky sync
# never shows up as a cron failure.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${SCRIPT_DIR}/.venv"
STATE_FILE="${SCRIPT_DIR}/.master_sync_last_run"
LOCK_FILE="${SCRIPT_DIR}/.master_sync.lock"
TODAY="$(date +%F)"

if command -v flock >/dev/null 2>&1; then
    exec 9>"${LOCK_FILE}"
    if ! flock -n 9; then
        echo "$(date -Is) [run_master_sync] a sync is already in progress, skipping."
        exit 0
    fi
else
    echo "$(date -Is) [run_master_sync] WARNING: flock not found, skipping overlap lock (day-guard below still applies)."
fi

if [[ "$(cat "${STATE_FILE}" 2>/dev/null || true)" == "${TODAY}" ]]; then
    echo "$(date -Is) [run_master_sync] already ran today (${TODAY}), skipping."
    exit 0
fi

cd "${SCRIPT_DIR}" || exit 0

if [[ -f "${VENV_DIR}/bin/activate" ]]; then
    # shellcheck disable=SC1091
    source "${VENV_DIR}/bin/activate"
fi

python3 Master.py
STATUS=$?
echo "${TODAY}" > "${STATE_FILE}"
echo "$(date -Is) [run_master_sync] finished with exit code ${STATUS}."
exit 0
