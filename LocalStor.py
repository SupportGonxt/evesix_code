"""Manual utility: push one local SQLite table up to Cloudflare D1.

NOTE: this script is not wired into startup/cron/pages.py, and hasn't
been for a while - the Settings screen's "sync" button only ever ran
Master.py + cloudSync.py (see pages.py's run_scripts_with_progress).
bulb_replace, which this script used to push, is now flushed
automatically by cloudSync.py's sync_bulb_replace() alongside data_q,
so you normally don't need to run this at all.

It's kept as a standalone tool for ad-hoc pushes - e.g. if you ever add
a new local table that isn't covered by cloudSync.py yet and want to
push it up by hand:

    python3 LocalStor.py bulb_replace
    python3 LocalStor.py some_other_table
"""
import sys

import cf_d1
import db

CHUNK_SIZE = 10  # see cloudSync.py for why this is kept small


def push_table(conn, table_name):
    cur = conn.cursor()
    cur.execute(f"SELECT * FROM {table_name}")
    rows = cur.fetchall()
    if not rows:
        print(f"No rows found in local table '{table_name}'.")
        return 0

    columns = rows[0].keys()
    placeholders = ", ".join(["?"] * len(columns))
    columns_list = ", ".join(columns)
    insert_prefix = f"INSERT OR REPLACE INTO {table_name} ({columns_list}) VALUES "

    pushed = 0
    for i in range(0, len(rows), CHUNK_SIZE):
        batch = rows[i:i + CHUNK_SIZE]
        values_parts = []
        params = []
        for row in batch:
            values_parts.append(f"({placeholders})")
            params.extend(row[col] for col in columns)
        sql = insert_prefix + ",".join(values_parts)
        meta = cf_d1.execute(sql, params)
        pushed += meta.get("changes", meta.get("rows_written", len(batch)))
        print(f"  Batch {i // CHUNK_SIZE + 1}: pushed {len(batch)} row(s).")

    print(f"Data synced to table '{table_name}' successfully. total_pushed={pushed}")
    return pushed


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 LocalStor.py <table_name>")
        sys.exit(1)
    table_name = sys.argv[1]

    if not cf_d1.is_configured():
        print("Cloudflare D1 credentials are not configured (see cf_d1.py). Aborting push.")
        sys.exit(1)

    conn = db.get_connection()
    try:
        push_table(conn, table_name)
    except cf_d1.D1Error as e:
        print(f"Error pushing '{table_name}' to D1: {e}")
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
