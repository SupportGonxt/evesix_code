"""Push queued local data up to Cloudflare D1.

This is the local -> cloud half of the sync (the other half, pulling
reference data cloud -> local, is Master.py). It replaces the old
"local MariaDB -> AWS RDS MariaDB" version of this script.

What changed from the MySQL version:
  - The local side is now the SQLite file managed by db.py instead of a
    MariaDB server on localhost - no DB server, no password, just a file.
  - The cloud side is now Cloudflare D1, reached over HTTPS via
    cf_d1.py instead of a MySQL TCP connection to an AWS RDS instance.
  - There is no longer a separate LocalStor.py process for bulb_replace:
    this script now flushes both data_q AND bulb_replace in one run,
    since both use the same "local row, unsynced flag" pattern.
  - D1 caps how many bound parameters a single statement can carry, so
    rows are batched in small groups (CHUNK_SIZE) rather than the large
    500-row batches the old MySQL version used.

Still runs the same way it always did: launched in the background at
boot (startup.sh / systemd), and on-demand from the Settings screen's
"sync" button (pages.py).
"""
import platform
import socket
import sys
import time

import cf_d1
import db

# Conservative row-batch size for multi-row INSERTs sent to D1. Each
# device_data row binds 9 parameters and each bulb_replace row binds 5;
# 10 rows per batch stays comfortably under D1's per-statement bound
# parameter ceiling. Raise this if you've confirmed your D1 plan allows
# more bound parameters per query.
CHUNK_SIZE = 10


def check_internet(host="8.8.8.8", port=53, timeout=3):
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        return True
    except socket.error:
        return False


def wait_for_internet():
    print("Checking for internet connection (fast backoff)...")
    start = time.time()
    attempts = 0
    while not check_internet():
        attempts += 1
        wait = min(10, 1 + attempts)
        print(f"No internet connection. Attempt {attempts}. Retrying in {wait}s...")
        time.sleep(wait)
    print(f"Internet connection established after {attempts} attempts in {round(time.time() - start, 2)}s.")


def sync_data_q(conn):
    """Push unsynced device-usage rows (data_q) up to D1's device_data table."""
    print("Fetching unsynced rows from local data_q (Update_status='no') ...")
    fetch_start = time.time()
    cur = conn.cursor()
    cur.execute(
        "SELECT D_Number, Start_date, End_date, Diagnostic, Code, Serial, Operator_Id, Bed_Id, Side "
        "FROM data_q WHERE Update_status = 'no'"
    )
    rows = cur.fetchall()
    total_rows = len(rows)
    print(f"Fetched {total_rows} unsynced rows in {round(time.time() - fetch_start, 3)}s.")

    if not total_rows:
        print("No unsynced data_q rows found; skipping device_data upload.")
        return 0, "", ""

    start_record = rows[0]["D_Number"]
    end_record = rows[-1]["D_Number"]

    insert_prefix = (
        "INSERT OR IGNORE INTO device_data "
        "(D_Number, Serial, Start_date, End_date, Diagnostic, Code, Operator_Id, Bed_Id, Side, Insert_date) VALUES "
    )
    actual_inserted = 0
    insert_start = time.time()
    for i in range(0, total_rows, CHUNK_SIZE):
        batch = rows[i:i + CHUNK_SIZE]
        values_parts = []
        params = []
        for r in batch:
            values_parts.append("(?,?,?,?,?,?,?,?,?,datetime('now','localtime'))")
            params.extend([
                r["D_Number"], r["Serial"], r["Start_date"], r["End_date"], r["Diagnostic"], r["Code"],
                r["Operator_Id"], r["Bed_Id"], r["Side"],
            ])
        insert_sql = insert_prefix + ",".join(values_parts)
        try:
            meta = cf_d1.execute(insert_sql, params)
        except cf_d1.D1Error as e:
            print(f"Bulk insert error (rows {i}-{i + len(batch) - 1}): {e}")
            continue
        batch_inserted = meta.get("changes", meta.get("rows_written", len(batch)))
        actual_inserted += batch_inserted
        print(f"Batch {i // CHUNK_SIZE + 1}: attempted={len(batch)} inserted={batch_inserted} ignored={len(batch) - batch_inserted}")
    insert_elapsed = time.time() - insert_start
    print(
        f"Bulk insert phase complete in {round(insert_elapsed, 3)}s. "
        f"total_attempted={total_rows} total_inserted={actual_inserted} total_ignored={total_rows - actual_inserted}"
    )

    # Sample verification: check existence of up to 3 representative D_Number keys.
    sample_keys = [rows[0]["D_Number"]]
    if total_rows > 1:
        sample_keys.append(rows[-1]["D_Number"])
    if total_rows > 2:
        sample_keys.append(rows[total_rows // 2]["D_Number"])
    placeholders = ",".join(["?"] * len(sample_keys))
    try:
        found = cf_d1.query(f"SELECT D_Number FROM device_data WHERE D_Number IN ({placeholders})", sample_keys)
        present = {r["D_Number"] for r in found}
        missing_samples = [k for k in sample_keys if k not in present]
        print(f"Sample verification: present={len(present)} missing={len(missing_samples)} -> missing_keys={missing_samples}")
    except cf_d1.D1Error as e:
        print(f"Sample verification query error: {e}")

    # Mark all previously-unsynced rows as synced now that D1 has them (or ignored true dupes).
    try:
        update_cur = conn.cursor()
        update_cur.execute("UPDATE data_q SET Update_status='yes' WHERE Update_status='no'")
        print("Marked all previously unsynced local rows as 'yes'.")
    except Exception as e:
        print(f"Failed to update local data_q statuses: {e}")

    return actual_inserted, start_record, end_record


def sync_bulb_replace(conn):
    """Push unsynced bulb-replacement rows up to D1's bulb_replace table."""
    print("Fetching unsynced rows from local bulb_replace (Sync_status='no') ...")
    cur = conn.cursor()
    cur.execute("SELECT BR_ID, Bulb_Num, Replacement_date, Serial, Sync_status FROM bulb_replace WHERE Sync_status = 'no'")
    rows = cur.fetchall()
    total_rows = len(rows)
    if not total_rows:
        print("No unsynced bulb_replace rows found; skipping.")
        return 0

    insert_prefix = "INSERT OR IGNORE INTO bulb_replace (BR_ID, Bulb_Num, Replacement_date, Serial, Sync_status) VALUES "
    actual_inserted = 0
    for i in range(0, total_rows, CHUNK_SIZE):
        batch = rows[i:i + CHUNK_SIZE]
        values_parts = []
        params = []
        for r in batch:
            values_parts.append("(?,?,?,?,?)")
            params.extend([r["BR_ID"], r["Bulb_Num"], r["Replacement_date"], r["Serial"], "yes"])
        insert_sql = insert_prefix + ",".join(values_parts)
        try:
            meta = cf_d1.execute(insert_sql, params)
        except cf_d1.D1Error as e:
            print(f"bulb_replace bulk insert error (rows {i}-{i + len(batch) - 1}): {e}")
            continue
        actual_inserted += meta.get("changes", meta.get("rows_written", len(batch)))

    try:
        update_cur = conn.cursor()
        update_cur.execute("UPDATE bulb_replace SET Sync_status='yes' WHERE Sync_status='no'")
        print("Marked all previously unsynced local bulb_replace rows as 'yes'.")
    except Exception as e:
        print(f"Failed to update local bulb_replace statuses: {e}")

    print(f"bulb_replace sync complete. total_attempted={total_rows} total_inserted={actual_inserted}")
    return actual_inserted


def write_sync_log(conn, start_time, end_time, missing_count, start_record, end_record):
    sync_insert = (
        "INSERT OR IGNORE INTO sync_log "
        "(Sync_log_Id, Operation_type, Start_date, End_date, Number_Of_Records, Start_record, End_record, Output) "
        "VALUES (? || ' ' || ?, ?, ?, ?, ?, ?, ?, ?)"
    )
    end_time_str = time.strftime('%Y-%m-%d %H:%M:%S', end_time)
    start_time_str = time.strftime('%Y-%m-%d %H:%M:%S', start_time)
    sync_values = (
        platform.node(), end_time_str, "Data Upload", start_time_str, end_time_str,
        missing_count, start_record, end_record, "Upload Complete",
    )
    try:
        cf_d1.execute(sync_insert, sync_values)
        print("Sync log entry inserted (or already existed).")
    except cf_d1.D1Error as e:
        print(f"Failed to insert sync log entry: {e}")


def main():
    start_time = time.localtime()
    wait_for_internet()

    if not cf_d1.is_configured():
        print("Cloudflare D1 credentials are not configured (see cf_d1.py). Aborting sync.")
        sys.exit(1)

    conn = db.get_connection()
    try:
        missing_count, start_record, end_record = sync_data_q(conn)
        sync_bulb_replace(conn)

        end_time = time.localtime()
        write_sync_log(conn, start_time, end_time, missing_count, start_record, end_record)

        conn.commit()
        total_elapsed = time.time() - time.mktime(start_time)
        print(
            f"SUMMARY: inserted={missing_count} total_duration={round(total_elapsed, 3)}s (net_wait_included)"
        )
    except Exception as e:
        print(f"Unexpected error during sync: {e}")
        sys.exit(1)
    finally:
        conn.close()
        print("Local connection closed. Script complete.")


if __name__ == "__main__":
    main()
