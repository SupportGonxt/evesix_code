#!/usr/bin/env python3
"""
One-time local fix: drop the incorrect UNIQUE(Username) constraint on the
operator table in this robot's local SQLite file.

Username is legitimately shared between operators (e.g. common first
names); only CODE is meant to be unique. D1's operator table had the same
bug and was already fixed there (see resync_mysql_to_d1.py history) -
this applies the equivalent fix locally so Master.py's reference-table
pull can insert every operator row without hitting a spurious UNIQUE
conflict.

Safe to run: backs up the current operator rows to operator_local_backup
.json first, verifies the actual constraint before changing anything, and
performs the table swap inside a single transaction with foreign key
enforcement off for that transaction only (restored afterward). If the
schema doesn't look like the expected bug pattern, it aborts without
making any change.

Usage (on the robot):
    python3 fix_operator_local_schema.py
"""
import json
import sqlite3
import sys

import db


def get_columns(conn, table):
    return conn.execute(f"PRAGMA table_info({table})").fetchall()


def get_unique_indexes(conn, table):
    """Return {index_name: [columns]} for indexes on `table` that enforce UNIQUE."""
    indexes = {}
    for idx in conn.execute(f"PRAGMA index_list({table})").fetchall():
        if not idx["unique"]:
            continue
        cols = [r["name"] for r in conn.execute(f"PRAGMA index_info({idx['name']})").fetchall()]
        indexes[idx["name"]] = cols
    return indexes


def get_foreign_keys(conn, table):
    return conn.execute(f"PRAGMA foreign_key_list({table})").fetchall()


def main():
    conn = sqlite3.connect(db.DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=OFF")  # this connection only

    columns = get_columns(conn, "operator")
    if not columns:
        print("No 'operator' table found locally. Aborting.")
        sys.exit(1)

    unique_indexes = get_unique_indexes(conn, "operator")
    username_unique = any("Username" in cols and len(cols) == 1 for cols in unique_indexes.values())
    code_unique = any("CODE" in cols and len(cols) == 1 for cols in unique_indexes.values())

    print("Current operator columns:", [c["name"] for c in columns])
    print("Current unique indexes:", unique_indexes)

    if not username_unique:
        print("No single-column UNIQUE constraint on Username found - schema doesn't "
              "match the expected bug pattern. Not making any change.")
        sys.exit(0)

    if not code_unique:
        print("WARNING: expected CODE to already be UNIQUE but it isn't. Aborting "
              "rather than guess at the right fix.")
        sys.exit(1)

    fks = get_foreign_keys(conn, "operator")
    print("Foreign keys on operator:", [(fk["from"], fk["table"], fk["to"]) for fk in fks])

    before_count = conn.execute("SELECT COUNT(*) c FROM operator").fetchone()["c"]
    print(f"operator row count before migration: {before_count}")

    backup_rows = [dict(r) for r in conn.execute("SELECT * FROM operator").fetchall()]
    with open("operator_local_backup.json", "w", encoding="utf-8") as f:
        json.dump(backup_rows, f, indent=2)
    print(f"Backed up {len(backup_rows)} rows to operator_local_backup.json")

    col_defs = []
    for c in columns:
        line = f'{c["name"]} {c["type"]}'
        if c["name"] == "Operator_Id":
            line += " PRIMARY KEY"
        if c["name"] == "CODE":
            line += " UNIQUE"
        if c["notnull"]:
            line += " NOT NULL"
        col_defs.append(line)
    for fk in fks:
        col_defs.append(f'FOREIGN KEY ({fk["from"]}) REFERENCES {fk["table"]}({fk["to"]})')

    create_sql = "CREATE TABLE operator_new (\n    " + ",\n    ".join(col_defs) + "\n)"
    print("\nNew schema:\n" + create_sql)

    col_names = ", ".join(c["name"] for c in columns)

    try:
        conn.execute("BEGIN")
        conn.execute(create_sql)
        conn.execute(f"INSERT INTO operator_new ({col_names}) SELECT {col_names} FROM operator")
        conn.execute("DROP TABLE operator")
        conn.execute("ALTER TABLE operator_new RENAME TO operator")
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Migration failed, rolled back, nothing changed: {e}")
        sys.exit(1)
    finally:
        conn.execute("PRAGMA foreign_keys=ON")

    after_count = conn.execute("SELECT COUNT(*) c FROM operator").fetchone()["c"]
    new_schema = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='operator'"
    ).fetchone()["sql"]
    print(f"\noperator row count after migration: {after_count}")
    print("Confirmed new schema:\n" + new_schema)
    conn.close()

    if after_count != before_count:
        print("WARNING: row count changed across the migration - investigate before trusting this table.")
        sys.exit(1)

    print("\nDone. Re-run Master.py now.")


if __name__ == "__main__":
    main()
