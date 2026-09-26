"""Cloudflare D1 REST API client.

This replaces the old "AWS RDS MySQL" cloud connection. D1 has no host/
port/socket to connect to - it is reached over plain HTTPS via
Cloudflare's REST API, authenticated with an API token instead of a
username/password.

Because D1 speaks the same SQL dialect as SQLite (it *is* SQLite under
the hood), the exact same SQL strings used locally against db.py's
sqlite3 connection - '?' placeholders, INSERT OR IGNORE, datetime('now'),
etc. - work here unchanged. That is why db.py and cf_d1.py share
schema.py.

Credentials (never hardcoded):
    Set these three environment variables (e.g. in the systemd service
    file via `Environment=`, or in the shell that launches dashboard.py
    / cloudSync.py):
        CF_ACCOUNT_ID       - Cloudflare account ID
        CF_D1_DATABASE_ID   - the D1 database's ID (not its name)
        CF_API_TOKEN        - an API token with "D1 Edit" permission
                               for that account

    If any of those aren't set as environment variables, this module
    falls back to reading them from d1_config.json next to this file
    (copy d1_config.example.json to d1_config.json and fill it in).
    d1_config.json holds secrets - keep it off USB sticks / shared
    drives and out of any code-sharing channel.
"""
import json
import os
import time

import requests

_CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "d1_config.json")

_API_BASE = "https://api.cloudflare.com/client/v4"


class D1Error(Exception):
    """Raised for any D1 request that fails (network, auth, or SQL error)."""


class D1ConfigError(D1Error):
    """Raised when Cloudflare credentials are missing or unreadable."""


def _load_config():
    account_id = os.environ.get("CF_ACCOUNT_ID")
    database_id = os.environ.get("CF_D1_DATABASE_ID")
    api_token = os.environ.get("CF_API_TOKEN")

    if not (account_id and database_id and api_token) and os.path.isfile(_CONFIG_PATH):
        try:
            with open(_CONFIG_PATH, "r") as f:
                cfg = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            raise D1ConfigError(f"Could not read {_CONFIG_PATH}: {e}") from e
        account_id = account_id or cfg.get("account_id")
        database_id = database_id or cfg.get("database_id")
        api_token = api_token or cfg.get("api_token")

    if not (account_id and database_id and api_token):
        raise D1ConfigError(
            "Cloudflare D1 credentials are missing. Set CF_ACCOUNT_ID, "
            "CF_D1_DATABASE_ID and CF_API_TOKEN as environment variables, "
            f"or copy d1_config.example.json to {_CONFIG_PATH} and fill it in."
        )
    return account_id, database_id, api_token


def _run(sql, params=None, timeout=15, retries=2):
    """POST one SQL statement to D1. Returns the raw per-statement result
    dict from Cloudflare's response, i.e. {'results': [...], 'meta': {...}}.
    """
    account_id, database_id, api_token = _load_config()
    url = f"{_API_BASE}/accounts/{account_id}/d1/database/{database_id}/query"
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json",
    }
    body = {"sql": sql, "params": list(params) if params else []}

    last_err = None
    for attempt in range(retries + 1):
        try:
            resp = requests.post(url, headers=headers, json=body, timeout=timeout)
        except requests.RequestException as e:
            last_err = e
            if attempt < retries:
                time.sleep(1 + attempt)
                continue
            raise D1Error(f"Network error calling D1: {e}") from e

        try:
            payload = resp.json()
        except ValueError as e:
            raise D1Error(
                f"D1 returned a non-JSON response (status {resp.status_code}): {resp.text[:300]}"
            ) from e

        if not resp.ok or not payload.get("success", False):
            errors = payload.get("errors") or payload.get("messages") or resp.text
            raise D1Error(f"D1 query failed (status {resp.status_code}): {errors}\nSQL: {sql}")

        results = payload.get("result") or []
        return results[0] if results else {"results": [], "meta": {}}

    raise D1Error(f"D1 request failed after retries: {last_err}")


def query(sql, params=None, timeout=15, retries=2):
    """Run a SELECT (or any statement whose rows you want) and return the
    matching rows as a list of dicts."""
    result = _run(sql, params, timeout=timeout, retries=retries)
    return result.get("results", [])


def execute(sql, params=None, timeout=15, retries=2):
    """Run an INSERT/UPDATE/DELETE/DDL statement. Returns the 'meta' dict
    D1 reports back, which includes 'rows_written' / 'changes' - the
    rough equivalent of mysql.connector's cursor.rowcount."""
    result = _run(sql, params, timeout=timeout, retries=retries)
    return result.get("meta", {})


def is_configured():
    """True if D1 credentials are available without raising. Useful for
    a quick pre-flight check before attempting a sync run."""
    try:
        _load_config()
        return True
    except D1ConfigError:
        return False
