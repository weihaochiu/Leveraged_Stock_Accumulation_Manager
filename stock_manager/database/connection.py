from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from stock_manager.config import DB_SCHEMA_VERSION
from .schema import DEFAULT_SETTINGS, SCHEMA_SQL


class Database:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=30000")
        return conn

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        conn = self.connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def initialize(self) -> None:
        with self.transaction() as conn:
            conn.executescript(SCHEMA_SQL)
            row = conn.execute("SELECT MAX(version) AS version FROM schema_info").fetchone()
            if row["version"] is None:
                conn.execute("INSERT INTO schema_info(version) VALUES (?)", (DB_SCHEMA_VERSION,))
            for key, value in DEFAULT_SETTINGS.items():
                conn.execute("INSERT OR IGNORE INTO settings(key,value) VALUES (?,?)", (key, value))

    def integrity_check(self) -> bool:
        with self.connect() as conn:
            return conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"

    def next_id(self, conn: sqlite3.Connection, name: str, prefix: str) -> str:
        conn.execute("INSERT OR IGNORE INTO sequences(name,value) VALUES (?,0)", (name,))
        conn.execute("UPDATE sequences SET value=value+1 WHERE name=?", (name,))
        value = conn.execute("SELECT value FROM sequences WHERE name=?", (name,)).fetchone()[0]
        return f"{prefix}-{value:06d}"

