"""Local database access for the robot dashboard.

Replaces the old MySQL/MariaDB connection (mysql.connector / pymysql to
localhost:'robotdb') with the robot's existing local SQLite file. There
is no server to run and no credentials to manage - just a file on disk.

IMPORTANT: /home/gonxt/robots-db/robotdb already has its real schema
and real data (confirmed to match the D1 side too). This module never
issues CREATE TABLE or any other DDL against it - it only opens a
connection and lets calling code run the same SQL that used to go to
MySQL (translated to SQLite syntax: %s -> ?, NOW() -> datetime('now'),
etc.). See schema.py for notes on what schema.py is (and isn't) used
for now.

Usage (mirrors the old mysql.connector pattern closely so call sites
only need their SQL translated, not restructured):

    import db
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT Operator_Id FROM operator WHERE code = ?", (code,))
    row = cur.fetchone()
    conn.commit()
    conn.close()
"""
import os
import sqlite3

# Points at the robot's actual local database (/home/gonxt/robots-db/robotdb).
# Override with the ROBOT_DB_PATH environment variable for local dev/testing
# off-device. This file's schema is managed outside of this codebase - see
# the module docstring.
DB_PATH = os.environ.get("ROBOT_DB_PATH", "/home/gonxt/robots-db/robotdb")


def get_connection(row_factory=True):
    """Open a connection to the local robot database.

    Multiple processes (dashboard.py, cloudSync.py, the pages.py "sync"
    subprocess calls, etc.) can all touch this file around the same
    time, so WAL mode + a busy timeout are used to avoid spurious
    "database is locked" errors instead of a MySQL-style server that
    handled that for us. No schema changes are made here.
    """
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=30000")
    if row_factory:
        conn.row_factory = sqlite3.Row
    return conn
