# Release Notes - Version 1.5
**Date:** November 5, 2025  
**Scope:** Sync performance, deployment tooling, DB robustness, incremental improvements  
**Status:** Performance & Ops Enhancement

---

## Summary
Version 1.2 focuses on dramatically reducing cloud sync time, improving operational deployment repeatability, and hardening database write error handling during success/error cycle recording. Previously a manual sync could take up to ~7 minutes; new bulk operations should reduce that to a few seconds (dependent on network & row count).

---

## Key Changes Since v1.1

### 1. Cloud Sync Optimization (`cloudSync.py`)
- Replaced per-row SELECT + INSERT pattern with batched `INSERT IGNORE` (default batch size: 500 rows).
- Removed redundant full-table scan of `sync_log` (now only inserts the current run's summary entry).
- Consolidated local status updates into a single `UPDATE data_q SET Update_status='yes' WHERE Update_status='no'` statement.
- Added timing metrics (fetch, insert phase, commit, total including network wait) and rows/sec estimate.
- Added backoff-based internet connectivity check (short waits first, capped at 10s).
- Result: Large syncs now scale approximately linearly with batches rather than O(N round-trips).

### 2. Incremental Sync Behavior (Clarification)
- Sync only processes rows where `Update_status='no'` — unchanged from prior behavior, but now explicitly documented.
- Uses `INSERT IGNORE` to avoid duplicate violation overhead (assumes `D_Number` unique/PK in cloud table).

### 3. Database Write Hardening (`pageOne.py`)
- Wrapped success and motion failure record persistence in `try/except/finally` blocks.
- Distinct logging for step 6 (success commit) and step 7 (motion commit) failures with `log_error` context.
- Ensures DB cursors/connections are closed even on exception (prevents resource leaks / partial locks).

### 4. Deployment & Operations Tooling
- Added `deploy_robot.sh` one-command provisioning & upgrade script:
    * Kills old processes (unless `--no-kill`).
    * Clones or updates repo branch.
    * Creates/updates virtual environment & installs dependencies from new `requirements.txt`.
    * Installs either systemd service (default) or cron-based startup (`--cron`).
    * Supports `--force` reclone, custom branch, custom repo URL.
- Added `requirements.txt` to formalize Python dependency set.
- Added `PI_SETUP.md` documenting manual provisioning (Pi OS config, MariaDB, venv, cron/systemd, troubleshooting).

### 5. Logging & Observability
- Added summary line in sync script: `SUMMARY: rows=<count> inserted_or_ignored=<n> total_duration=<sec>`.
- Step-based logging already introduced in v1.1 now extended with clearer DB failure semantics.

### 6. Safety / Consistency Improvements
- Avoids repeated closing/reopening of DB connections inside loops.
- Eliminated row-by-row existence checks (previously required one SELECT per candidate row → high latency on remote links).
- Reduced risk of partial updates: commit is atomic for all inserted/ignored rows plus status update.

---

## Performance Comparison (Illustrative Example)
| Scenario | Old Method (Row Query + Insert + Update) | New Method (Batched) |
|----------|------------------------------------------|----------------------|
| 1,000 unsynced rows | ~1,000 network round-trips + UPDATE per row | ~2–4 round-trips (2 insert batches + 1 update + 1 commit) |
| Duplicate handling | Per-row SELECT + conditional INSERT | INSERT IGNORE (server-side skip) |
| Local status update | 1 UPDATE per row | Single bulk UPDATE |
| Sync log replication | Copies all prior logs each run | Inserts only current run |

Actual timing will depend on WAN latency to the cloud database, but improvements are multiplicative for higher row counts.

---

## Upgrade Notes (v1.1 → v1.2)
No schema changes introduced. To benefit from performance gains, ensure:
1. Cloud `device_data` table enforces uniqueness/primary key on `D_Number` (required for `INSERT IGNORE` semantics to be meaningful).
2. Adequate MariaDB connection limits (batched inserts may briefly increase packet size).
3. `requirements.txt` is installed in your runtime environment.

Optional (future) enhancements not yet applied:
- Add index on `data_q(Update_status)` if row volume becomes large.
- Switch from `INSERT IGNORE` to `INSERT ... ON DUPLICATE KEY UPDATE` if field corrections are needed for already-synced rows.

---

## New Files / Artifacts
| File | Purpose |
|------|---------|
| `deploy_robot.sh` | Automated deployment / upgrade script (systemd or cron) |
| `requirements.txt` | Formal dependency manifest (kivy, mysql-connector-python, PyMySQL, gpiozero, rpi5-ws2812, lgpio, psutil, requests) |
| `PI_SETUP.md` | Manual provisioning runbook |

---

## Known Limitations (Unchanged / Newly Noted)
1. Sync does not reconcile modified rows already marked `yes` (no change detection).  
2. Time fields are passed as original local structures; future improvement: standardize to UTC ISO-8601.  
3. No retry logic on transient cloud DB network errors inside batch insert (will log and continue).  
4. If `D_Number` uniqueness is not enforced, duplicates may accumulate silently.  

---

## Next Candidate Enhancements (Proposed for v1.3)
1. Add checksum / audit mode for periodic integrity validation.
2. Introduce retry with exponential backoff for failed batches.
3. Optional asynchronous sync trigger immediately after each successful cycle (background thread).
4. Structured log to file (JSON lines) for ingestion.
5. Environment variable configuration for DB creds (remove hard-coded passwords).

---

## Version History
- **v1.5** (Nov 5, 2025) - Bulk sync optimization, deployment tooling, DB write hardening.
- **v1.1** (Nov 3, 2025) - Critical bug fixes for freezing and LED control.
- **v1.0** - Initial release with known issues.

---

**End of Release Notes v1.5**

---

# Release Notes - Version 1.1
**Date:** November 3, 2025  
**File:** pageOne.py  
**Status:** Bug Fix Release

---

## Overview
This release fixes critical issues where the robot would freeze at the end of a cycle, LEDs would not change state properly, and the system would become unresponsive due to blocking database operations.

---

## Issues Fixed

### 1. **Robot Freezing at Cycle Completion**
- **Issue:** Machine would stop responding at 00:01 remaining
- **Root Cause:** Database operations blocking the main thread before UI updates
- **Fix:** Reordered operations to update LEDs and UI before database writes

### 2. **LEDs Not Changing State**
- **Issue:** LEDs remained stuck in previous state after cycle completion
- **Root Cause:** LED control code executed after blocking database operations
- **Fix:** Moved LED control to top of completion handler

### 3. **Incorrect LED Colors**
- **Issue:** LEDs not showing correct colors for different states
- **Root Cause:** Wrong color codes and execution order
- **Fix:** Set proper colors: Blue for error, Green for success

### 4. **Missing Error Handling**
- **Issue:** Sensor read errors could crash the countdown
- **Root Cause:** No exception handling around sensor.distance calls
- **Fix:** Added try/except blocks around all sensor reads

### 5. **Code Continues After Motion Detection**
- **Issue:** Motion detection handler didn't exit properly
- **Root Cause:** Missing return statement after handling motion
- **Fix:** Added return statement to prevent further execution

---

## Critical Change: Execution Order Comparison

### ❌ **BEFORE (v1.0) - BROKEN ORDER:**
```
When countdown reaches 0 (Success):
├─ 1. Unschedule countdown timer               ✅ OK
├─ 2. Update label to "SUCCESSFUL"             ✅ OK
├─ 3. Turn off relay (UV bulbs)                ✅ OK
├─ 4. Open database connection                 ⚠️  BLOCKS HERE
├─ 5. Execute SQL INSERT                       ⚠️  BLOCKS HERE
├─ 6. Commit to database                       ⚠️  BLOCKS HERE
├─ 7. Close database                           ⚠️  BLOCKS HERE
├─ 8. Create "Done" button                     ❌ NEVER REACHED
├─ 9. Add button to layout                     ❌ NEVER REACHED
├─ 10. Change LEDs                             ❌ NEVER REACHED (STUCK)
└─ 11. Start beeping                           ❌ NEVER REACHED

RESULT: Screen freezes, LEDs stuck, no beep, user sees "00:01" frozen
```

### ✅ **AFTER (v1.1) - CORRECT ORDER:**
```
When countdown reaches 0 (Success):
├─ 1. Unschedule countdown timer               ✅ IMMEDIATE
├─ 2. Change LEDs to GREEN                     ✅ IMMEDIATE (MOVED UP!)
├─ 3. Update label to "SUCCESSFUL"             ✅ IMMEDIATE
├─ 4. Turn off relay (UV bulbs)                ✅ IMMEDIATE
├─ 5. Open database connection                 ⏳ Can block (but UI already updated)
├─ 6. Execute SQL INSERT                       ⏳ Can block
├─ 7. Commit to database                       ⏳ Can block
├─ 8. Close database                           ⏳ Can block
├─ 9. Start beeping                            ✅ Happens after DB (MOVED UP!)
├─ 10. Create "Done" button                    ✅ Works
├─ 11. Add button to layout                    ✅ Works
└─ 12. User clicks "Done" to continue          ✅ Works

RESULT: LEDs turn green immediately, beeping starts, button works, no freeze
```

---

## Detailed Changes

### Change 1: Added Sensor Error Handling
**Location:** Lines 876-892  
**Type:** Enhancement

```python
# Before:
current_distance = sensor.distance * 100

# After:
try:
    current_distance = sensor.distance * 100
except Exception as e:
    print(f"Sensor read error: {e}")
    current_distance = self.previous_distance  # Use last known good value
```

**Impact:** Prevents crashes if sensor read fails

---

### Change 2: LED Color on Motion Detection
**Location:** Line 919-922  
**Type:** Bug Fix

```python
# Before:
self.strip.set_all_pixels(Color(0, 0, 0))  # OFF
print("LEDs turned OFF after motion detection")

# After:
self.strip.set_all_pixels(Color(0, 0, 255))  # BLUE
print("LEDs turned BLUE after motion detection")
```

**Impact:** Clear visual indicator that motion was detected

---

### Change 3: Added Return After Motion Detection
**Location:** Line 985  
**Type:** Bug Fix

```python
self.start_long_beeping()
return  # Exit after handling motion detection to prevent further execution
```

**Impact:** Prevents code from continuing after motion error

---

### Change 4: Update Baseline Distance
**Location:** Lines 987-989  
**Type:** Bug Fix

```python
else:   
    print("in else - no motion detected")
    self.previous_distance = current_distance  # Update baseline for next check
```

**Impact:** Prevents false motion detection from stale baseline

---

### Change 5: **CRITICAL** - Moved LED Control to Top
**Location:** Lines 1001-1004  
**Type:** Critical Bug Fix

```python
# Before: LED control was at line ~1039 (after database operations)

# After: LED control moved to line 1001 (before database operations)
Clock.unschedule(self.update_ten_minute_countdown)

# CRITICAL: Turn LEDs green and update UI FIRST before database operations
self.strip.set_all_pixels(Color(0, 255, 0))  # Turn LEDs GREEN for success
self.strip.show()
print("LEDs turned GREEN after successful cycle")

self.countdown_label.text = "SUCCESSFUL"
# ... then relay, then database ...
```

**Impact:** LEDs change immediately, even if database hangs

---

### Change 6: Moved Beeping Start Earlier
**Location:** Line 1031  
**Type:** Bug Fix

```python
# Before: Beeping started at line ~1043 (after button creation)

# After: Beeping starts at line 1031 (right after database)
mydb.close()
print("`Success` DB written - database operations complete")

# Start beeping before creating button
self.start_beeping()
```

**Impact:** Audio feedback happens reliably

---

### Change 7: Added Debug Logging
**Location:** Multiple  
**Type:** Enhancement

```python
# Added throughout code:
print("=" * 50)
print("CYCLE COMPLETED SUCCESSFULLY - COUNTDOWN REACHED 0")
print("=" * 50)
print("Starting database write...")
print("`Success` DB written - database operations complete")
print(f"Countdown: {minutes:02}:{seconds:02} ({self.countdown_time} seconds remaining)")
print("Done button added - cycle complete")
```

**Impact:** Easier debugging and troubleshooting

---

## LED State Reference

| State | Color | RGB | When |
|-------|-------|-----|------|
| Initial Countdown | Orange | (255, 165, 0) | User leaving room |
| Warm-up Start | Red | (255, 0, 0) | First 60 seconds |
| Active Cycle | Green | (0, 255, 0) | Normal operation |
| Motion Error | Blue | (0, 0, 255) | Motion detected |
| Success | Green | (0, 255, 0) | Cycle completed |

---

## Testing Recommendations

### Test Case 1: Normal Cycle Completion
1. Start robot with normal settings
2. Let countdown complete fully to 00:00
3. **Expected:** LEDs turn green immediately, beeping starts, "Done" button appears
4. **Verify:** No screen freeze, data syncs to database

### Test Case 2: Motion Detection
1. Start robot
2. Trigger motion during cycle
3. **Expected:** LEDs turn blue, error message displays, beeping starts
4. **Verify:** "Done" button appears, data syncs with error status

### Test Case 3: Sensor Failure
1. Disconnect sensor temporarily
2. Start cycle
3. **Expected:** Countdown continues using last known value
4. **Verify:** No crash, error logged to console

### Test Case 4: Database Slow Response
1. Simulate slow database (add delay in DB)
2. Complete cycle
3. **Expected:** LEDs turn green immediately despite DB delay
4. **Verify:** UI responsive, beeping starts, button eventually appears

---

## Rollback Instructions

If issues arise, revert the following changes in this order:

1. Revert LED control position (move back to bottom)
2. Revert beeping position (move back to bottom)
3. Remove sensor error handling
4. Remove return statement after motion detection
5. Remove debug logging

**Command:**
```bash
git revert <commit-hash>
```

---

## Migration Notes

**No database schema changes required**  
**No configuration changes required**  
**No dependencies added or removed**  
**Compatible with existing hardware**

---

## Known Limitations

1. Display still shows "00:01" during the last second (by design)
2. Database writes still block the main thread (future enhancement: use threading)
3. Sensor error falls back to last known value (may not detect new motion if sensor fails)

---

## Future Enhancements

1. **Move database operations to background thread** - Prevent any blocking
2. **Add database write queue** - Handle slow network connections better
3. **Add database retry logic** - Handle connection failures gracefully
4. **Display "00:00"** - Show actual zero before success message
5. **Add LED test mode** - Verify LED colors during setup

---

## Contributors

- Bug fixes and performance improvements
- Enhanced error handling and user feedback
- Improved LED state management

---

## Version History

- **v1.1** (Nov 3, 2025) - Critical bug fixes for freezing and LED control
- **v1.0** (Previous) - Initial release with known issues

---

## Support

For issues or questions about this release:
- Check console output for debug messages
- Review LED state against reference table above
- Verify database connectivity if sync fails

---

**End of Release Notes v1.1**
