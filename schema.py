"""Table-name groupings used by the sync scripts.

Both the local SQLite file (/home/gonxt/robots-db/robotdb) and the D1
database (robots-db-preview) already have their real, matching schema
and data - this module does NOT define or create schema. It only
names which existing tables belong to which sync direction, so
Master.py/local.py know which tables to touch without hardcoding the
list in multiple places.
"""

# Reference/lookup tables Master.py pulls down cloud -> local.
REFERENCE_TABLES = ["hospital_group", "hospital", "ward", "bed", "robot", "operator"]

# Tables that are local write queues and must never be overwritten by a
# cloud -> local pull (they track this robot's own unsynced rows).
QUEUE_TABLES = ["data_q", "sync_log", "bulb_replace", "device_data"]
