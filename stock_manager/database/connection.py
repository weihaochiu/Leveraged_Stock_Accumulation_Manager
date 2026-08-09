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
            self._migrate(conn)
            row = conn.execute("SELECT MAX(version) AS version FROM schema_info").fetchone()
            if row["version"] is None:
                conn.execute("INSERT INTO schema_info(version) VALUES (?)", (DB_SCHEMA_VERSION,))
            elif int(row["version"]) < DB_SCHEMA_VERSION:
                conn.execute("INSERT INTO schema_info(version) VALUES (?)", (DB_SCHEMA_VERSION,))
            for key, value in DEFAULT_SETTINGS.items():
                conn.execute("INSERT OR IGNORE INTO settings(key,value) VALUES (?,?)", (key, value))

    @staticmethod
    def _migrate(conn: sqlite3.Connection) -> None:
        """以非破壞方式補齊舊版 SQLite 欄位。"""
        existing = {row["name"] for row in conn.execute("PRAGMA table_info(price_history)")}
        additions = {
            "exchange": "TEXT NOT NULL DEFAULT ''",
            "open_price": "REAL",
            "high_price": "REAL",
            "low_price": "REAL",
            "volume_shares": "INTEGER",
            "turnover_twd": "INTEGER",
            "transaction_count": "INTEGER",
            "price_change": "REAL",
            "quote_type": "TEXT NOT NULL DEFAULT 'CLOSE'",
            "fetched_at": "TEXT",
            "is_manual_override": "INTEGER NOT NULL DEFAULT 0",
            "warning_message": "TEXT NOT NULL DEFAULT ''",
        }
        for column, definition in additions.items():
            if column not in existing:
                conn.execute(f"ALTER TABLE price_history ADD COLUMN {column} {definition}")
        conn.execute(
            "UPDATE price_history SET fetched_at=COALESCE(fetched_at,updated_at), "
            "is_manual_override=CASE WHEN source IN ('MANUAL','手動輸入') THEN 1 ELSE is_manual_override END"
        )

    def integrity_check(self) -> bool:
        with self.connect() as conn:
            return conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"

    def next_id(self, conn: sqlite3.Connection, name: str, prefix: str) -> str:
        conn.execute("INSERT OR IGNORE INTO sequences(name,value) VALUES (?,0)", (name,))
        conn.execute("UPDATE sequences SET value=value+1 WHERE name=?", (name,))
        value = conn.execute("SELECT value FROM sequences WHERE name=?", (name,)).fetchone()[0]
        return f"{prefix}-{value:06d}"
