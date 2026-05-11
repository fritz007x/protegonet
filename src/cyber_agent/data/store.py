"""Data access layer — vendors, audit log, threat signatures.

SQLite-backed for local dev and tests; swap the connection for a hosted
database without touching callers.
"""
from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path
from typing import Any

from ..config import settings

_LOCK = threading.Lock()
_initialized_paths: set[str] = set()


def _conn() -> sqlite3.Connection:
    path = Path(settings.audit_db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(path)
    c.row_factory = sqlite3.Row
    return c


def init_db() -> None:
    path = str(Path(settings.audit_db_path).resolve())
    if path in _initialized_paths:
        return
    with _LOCK, _conn() as c:
        c.executescript(
            """
            CREATE TABLE IF NOT EXISTS vendors (
                supplier_id TEXT PRIMARY KEY,
                bank_account TEXT,
                avg_amount REAL,
                last_seen TEXT,
                metadata TEXT
            );
            CREATE TABLE IF NOT EXISTS email_baselines (
                sender TEXT PRIMARY KEY,
                avg_hour REAL,
                typical_recipients TEXT,
                tone TEXT,
                updated_at TEXT
            );
            CREATE TABLE IF NOT EXISTS threat_signatures (
                id TEXT PRIMARY KEY,
                type TEXT,
                pattern TEXT,
                embedding TEXT,
                source TEXT
            );
            CREATE TABLE IF NOT EXISTS audit_log (
                trace_id TEXT PRIMARY KEY,
                input_hash TEXT,
                decision TEXT,
                risk_score REAL,
                signals TEXT,
                human_feedback TEXT,
                ts TEXT
            );
            """
        )
    _initialized_paths.add(path)


def _row_to_vendor(row: sqlite3.Row | None) -> dict | None:
    if row is None:
        return None
    record = dict(row)
    raw_meta = record.get("metadata")
    if isinstance(raw_meta, str):
        try:
            record["metadata"] = json.loads(raw_meta)
        except json.JSONDecodeError:
            record["metadata"] = {}
    return record


def get_vendor(supplier_id: str) -> dict | None:
    if not supplier_id:
        return None
    init_db()
    with _LOCK, _conn() as c:
        row = c.execute(
            "SELECT * FROM vendors WHERE LOWER(supplier_id)=LOWER(?)",
            (supplier_id,),
        ).fetchone()
        return _row_to_vendor(row)


def upsert_vendor(
    supplier_id: str,
    bank_account: str | None = None,
    avg_amount: float | None = None,
    last_seen: str | None = None,
    metadata: dict | None = None,
) -> dict:
    init_db()
    with _LOCK, _conn() as c:
        row = c.execute(
            """
            INSERT INTO vendors(supplier_id, bank_account, avg_amount, last_seen, metadata)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(supplier_id) DO UPDATE SET
                bank_account=COALESCE(excluded.bank_account, vendors.bank_account),
                avg_amount=COALESCE(excluded.avg_amount, vendors.avg_amount),
                last_seen=COALESCE(excluded.last_seen, vendors.last_seen),
                metadata=COALESCE(excluded.metadata, vendors.metadata)
            RETURNING *
            """,
            (supplier_id, bank_account, avg_amount, last_seen, json.dumps(metadata or {})),
        ).fetchone()
        return _row_to_vendor(row)  # type: ignore[return-value]


def write_audit(record: dict[str, Any]) -> None:
    init_db()
    with _LOCK, _conn() as c:
        c.execute(
            """
            INSERT OR REPLACE INTO audit_log
            (trace_id, input_hash, decision, risk_score, signals, human_feedback, ts)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.get("trace_id"),
                record.get("input_hash"),
                record.get("decision"),
                record.get("risk_score"),
                json.dumps(record.get("signals") or []),
                json.dumps(record.get("human_feedback") or {}),
                record.get("ts"),
            ),
        )
