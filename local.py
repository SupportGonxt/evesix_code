"""Manual utility: push every locally-generated table up to Cloudflare D1
in one go.

Like LocalStor.py, this script is not wired into startup/cron/pages.py
- it's an earlier, broader draft of the same idea (push everything
instead of just one table). Routine syncing is handled automatically by
cloudSync.py (data_q, bulb_replace). Run this by hand only if you need
to force a full re-push of every local table, e.g. after recovering
from an outage:

    python3 local.py
"""
import sys

import cf_d1
import db
from LocalStor import push_table
from schema import REFERENCE_TABLES


def local_table_names(conn):
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    return [row["name"] for row in cur.fetchall()]


def main():
    if not cf_d1.is_configured():
        print("Cloudflare D1 credentials are not configured (see cf_d1.py). Aborting push.")
        sys.exit(1)

    conn = db.get_connection()
    try:
        tables = [t for t in local_table_names(conn) if t not in REFERENCE_TABLES]
        print(f"Pushing local tables to D1: {', '.join(tables) or '(none found)'}")
        for table_name in tables:
            try:
                push_table(conn, table_name)
            except cf_d1.D1Error as e:
                print(f"  {table_name}: FAILED: {e}")
        print("Full push complete.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
