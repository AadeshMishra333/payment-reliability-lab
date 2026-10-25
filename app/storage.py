"""SQLite persistence for one synthetic demo instance."""

from contextlib import contextmanager
from pathlib import Path
import os
import sqlite3

DEFAULT_DATABASE = Path(__file__).resolve().parents[1] / "data" / "payments.sqlite3"


class PaymentStore:
    def __init__(self, path: str | Path | None = None):
        self.path = Path(path or os.environ.get("DATABASE_PATH", DEFAULT_DATABASE))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS payments (
                    id TEXT PRIMARY KEY,
                    session TEXT NOT NULL,
                    request_key TEXT,
                    amount_minor INTEGER NOT NULL CHECK (amount_minor > 0),
                    currency TEXT NOT NULL CHECK (currency = 'INR'),
                    merchant_reference TEXT NOT NULL,
                    status TEXT NOT NULL CHECK (status IN ('pending', 'succeeded', 'failed')),
                    created_at TEXT NOT NULL,
                    UNIQUE (session, request_key)
                );
                CREATE INDEX IF NOT EXISTS payments_by_session ON payments(session);
            """)

    @contextmanager
    def connect(self, *, write: bool = False):
        conn = sqlite3.connect(self.path, timeout=15)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            if write:
                conn.execute("BEGIN IMMEDIATE")
            yield conn
            conn.commit()
        except BaseException:
            conn.rollback()
            raise
        finally:
            conn.close()
