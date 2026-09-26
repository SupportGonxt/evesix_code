"""Pull reference data down from Cloudflare D1 into the local SQLite file.

This is the cloud -> local half of the sync (the other half, pushing
locally-generated rows up, is cloudSync.py). It replaces the old
"AWS RDS MariaDB -> local MariaDB" version of this script.

Reference tables (hospital, hospital_group, ward, bed, robot, operator)
are maintained centrally in D1 and mirrored down to each robot so the
touchscreen can look up hospital/ward/bed/operator names without a
live connection during a cleaning cycle. device_data, data_q, sync_log
and bulb_replace are deliberately NOT pulled here - those are this
robot's own write queue and pulling them down would clobber pending
unsynced rows.

Invoked by the Settings screen's "sync" button (pages.py) before
cloudSync.py runs, and can also be run standalone:

    python3 Master.py
"""
import sys

import cf_d1
import db
from schema import REFERENCE_TABLES


def pull_table(conn, table_name):
    rows = cf_d1.query(f"SELECT * FROM {table_name}")
    if not rows:
        print(f"  {table_name}: no rows in D1, skipping.")
        return 0

    # First column is always this table's primary key (true for every table
    # in REFERENCE_TABLES). Upsert in place on conflict rather than
    # INSERT OR REPLACE: REPLACE resolves a PK conflict by deleting the
    # existing row first, which trips local FOREIGN KEY constraints from
    # this robot's own device_data rows that still reference it.
    columns = list(rows[0].keys())
    pk = columns[0]
    placeholders = ", ".join(["?"] * len(columns))
    columns_list = ", ".join(columns)
    other_columns = [c for c in columns if c != pk]
    if other_columns:
        update_clause = ", ".join(f"{c}=excluded.{c}" for c in other_columns)
        conflict_action = f"DO UPDATE SET {update_clause}"
    else:
        conflict_action = "DO NOTHING"
    insert_sql = (
        f"INSERT INTO {table_name} ({columns_list}) VALUES ({placeholders}) "
        f"ON CONFLICT({pk}) {conflict_action}"
    )

    param_rows = [tuple(row.get(col) for col in columns) for row in rows]
    conn.executemany(insert_sql, param_rows)
    conn.commit()
    print(f"  {table_name}: synced {len(param_rows)} row(s).")
    return len(param_rows)


def main():
    if not cf_d1.is_configured():
        print("Cloudflare D1 credentials are not configured (see cf_d1.py). Aborting pull.")
        sys.exit(1)

    conn = db.get_connection()
    try:
        print(f"Pulling reference tables from D1: {', '.join(REFERENCE_TABLES)}")
        total = 0
        for table_name in REFERENCE_TABLES:
            try:
                total += pull_table(conn, table_name)
            except cf_d1.D1Error as e:
                print(f"  {table_name}: FAILED: {e}")
        print(f"Reference data pull complete. total_rows_synced={total}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
