import mysql.connector
import time
import socket
import sys
import platform
from datetime import datetime

def check_internet(host="8.8.8.8", port=53, timeout=3):
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        return True
    except socket.error:
        return False

# Internet check loop
print("Checking for internet connection (fast backoff)...")
_net_start = time.time()
_attempts = 0
while not check_internet():
    _attempts += 1
    wait = min(10, 1 + _attempts)  # gradual backoff up to 10s max
    print(f"No internet connection. Attempt {_attempts}. Retrying in {wait}s...")
    time.sleep(wait)
print(f"Internet connection established after {_attempts} attempts in {round(time.time()-_net_start,2)}s.")

local_conn = master_conn = None
local_cursor = update_cursor = master_cursor = None
start_time = time.localtime() 
missing_count = 0;
start_record=  "";
end_record = "";
try:
    print("Connecting to local database...")
    local_conn = mysql.connector.connect(
        host='localhost',
        user='root',
        password='Robot123#',
        database='robotdb'
    )
    print("Connected to local database.")

    print("Connecting to cloud database...")
    master_conn = mysql.connector.connect(
        host='13.247.23.5',
        user='robot',
        password='robot123#',
        database='robotdb'
    )
    print("Connected to cloud database.")

    local_cursor = local_conn.cursor(dictionary=True)
    update_cursor = local_conn.cursor()
    master_cursor = master_conn.cursor()

    print("Fetching unsynced rows from local data_q (Update_status='no') ...")
    fetch_start = time.time()
    local_cursor.execute("SELECT D_Number, Start_date, End_date, Diagnostic, Code, Serial, Operator_Id, Bed_Id, Side FROM data_q WHERE Update_status = 'no'")
    rows = local_cursor.fetchall()
    fetch_elapsed = time.time() - fetch_start
    total_rows = len(rows)
    print(f"Fetched {total_rows} unsynced rows in {round(fetch_elapsed,3)}s.")

    if total_rows:
        start_record = rows[0]['D_Number']
        end_record = rows[-1]['D_Number']

        # Build bulk INSERT IGNORE to avoid per-row existence check.
        # Assumes D_Number is PRIMARY KEY or UNIQUE in cloud device_data.
        chunk_size = 500  # tune if needed
        insert_template_prefix = (
            "INSERT IGNORE INTO device_data "
            "(D_Number, Start_date, End_date, Diagnostic, Code, Serial, Operator_Id, Bed_Id, Side, Insert_date) VALUES "
        )
        insert_total_start = time.time()
        for i in range(0, total_rows, chunk_size):
            batch = rows[i:i+chunk_size]
            values_clause_parts = []
            params = []
            for r in batch:
                values_clause_parts.append("(%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW())")
                params.extend([
                    r['D_Number'], r['Start_date'], r['End_date'], r['Diagnostic'], r['Code'],
                    r['Serial'], r['Operator_Id'], r['Bed_Id'], r['Side']
                ])
            insert_sql = insert_template_prefix + ",".join(values_clause_parts)
            try:
                master_cursor.execute(insert_sql, params)
            except mysql.connector.Error as e:
                print(f"Bulk insert error (rows {i}-{i+len(batch)-1}): {e}")
            else:
                print(f"Inserted/ignored batch {i//chunk_size+1} containing {len(batch)} rows.")
        insert_elapsed = time.time() - insert_total_start

        # Estimate missing_count as number of rows attempted (IGNORE hides duplicates)
        missing_count = total_rows
        print(f"Bulk insert phase complete in {round(insert_elapsed,3)}s (approx {round(total_rows/max(insert_elapsed,0.001))} rows/sec).")

        # Single update: mark all unsynced rows as synced now.
        try:
            update_cursor.execute("UPDATE data_q SET Update_status='yes' WHERE Update_status='no'")
            print("Marked all previously unsynced local rows as 'yes'.")
        except mysql.connector.Error as e:
            print(f"Failed to update local statuses: {e}")
    else:
        print("No unsynced rows found; skipping bulk insert and update.")

    end_time = time.localtime()    
    # Insert just this run's sync log entry with INSERT IGNORE (avoid second table sweep)
    sync_id_end = end_time  # used for ID construction
    sync_insert = (
        "INSERT IGNORE INTO sync_log "
        "(Sync_log_Id, Operation_type, Start_date, End_date, Number_Of_Records, Start_record, End_record, Output) "
        "VALUES (CONCAT(%s,' ',%s), %s, %s, %s, %s, %s, %s, %s)"
    )
    sync_values = (
        platform.node(), sync_id_end, 'Data Upload', start_time, end_time,
        missing_count, start_record, end_record, 'Upload Complete'
    )
    try:
        master_cursor.execute(sync_insert, sync_values)
        print("Sync log entry inserted (or already existed).")
    except mysql.connector.Error as e:
        print(f"Failed to insert sync log entry: {e}")
    print("Committing changes to local and cloud databases...")
    commit_start = time.time()
    local_conn.commit()
    master_conn.commit()
    commit_elapsed = time.time() - commit_start
    total_elapsed = time.time() - _net_start  # includes network wait
    print(f"Commits complete in {round(commit_elapsed,3)}s.")
    print(f"SUMMARY: rows={total_rows} inserted_or_ignored={missing_count} total_duration={round(total_elapsed,3)}s (net_wait_included).")

except mysql.connector.Error as db_err:
    print(f"Database connection or query error: {db_err}")
    sys.exit(1)
except Exception as e:
    print(f"Unexpected error: {e}")
    sys.exit(1)
finally:
    print("Closing all cursors and connections...")
    try:
        if local_cursor: local_cursor.close()
        if update_cursor: update_cursor.close()
        if master_cursor: master_cursor.close()
        if local_conn: local_conn.close()
        if master_conn: master_conn.close()
        print("All connections closed. Script complete.")
    except Exception as close_err:
        print(f"Error during cleanup: {close_err}")