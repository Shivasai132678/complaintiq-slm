"""Parameterized SQLite persistence for complaint analysis records."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


class ComplaintStore:
    """Keep complete JSON records and query metadata in a small local database."""

    def __init__(self, db_path: str) -> None:
        self.path = Path(db_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS complaints (id TEXT PRIMARY KEY, created_at TEXT NOT NULL, record TEXT NOT NULL)"
            )

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(str(self.path), timeout=15)

    def save(self, record: dict[str, Any]) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO complaints(id, created_at, record) VALUES (?, ?, ?)",
                (record["id"], record["created_at"], json.dumps(record)),
            )

    def list(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            return [
                json.loads(row[0])
                for row in connection.execute(
                    "SELECT record FROM complaints ORDER BY created_at DESC, rowid DESC"
                )
            ]
