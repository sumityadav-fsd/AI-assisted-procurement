"""SQLite access (stdlib sqlite3, no ORM). OWNER: Member 3.

Design: documents are stored as JSON blobs keyed by id. We are a demo MVP, not a data warehouse.
Pydantic models are the source of truth; tables only persist and retrieve them.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS requirements (id TEXT PRIMARY KEY, created_at TEXT NOT NULL, payload TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS rfqs         (id TEXT PRIMARY KEY, created_at TEXT NOT NULL, payload TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS quotations   (id TEXT PRIMARY KEY, rfq_id TEXT NOT NULL, created_at TEXT NOT NULL, payload TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS comparisons  (id TEXT PRIMARY KEY, rfq_id TEXT NOT NULL, created_at TEXT NOT NULL, payload TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS shortlists   (comparison_id TEXT PRIMARY KEY, created_at TEXT NOT NULL, payload TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS approvals    (id TEXT PRIMARY KEY, comparison_id TEXT NOT NULL, created_at TEXT NOT NULL, payload TEXT NOT NULL);
"""


def connect(path: str) -> sqlite3.Connection:
    if path != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(path: str) -> None:
    conn = connect(path)
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()
