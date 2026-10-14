from __future__ import annotations

import json
import os
import sqlite3
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class CacheHit:
    value: dict[str, Any]
    state: str  # fresh | stale


class CacheStore:
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self._initialize()

    @contextmanager
    def _connect(self):
        connection = sqlite3.connect(self.path, timeout=5)
        try:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("PRAGMA busy_timeout=5000")
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()
            self._secure_permissions()

    def _secure_permissions(self) -> None:
        for candidate in (
            self.path,
            Path(str(self.path) + "-wal"),
            Path(str(self.path) + "-shm"),
        ):
            try:
                os.chmod(candidate, 0o600)
            except FileNotFoundError:
                pass

    def _initialize(self) -> None:
        with self._connect() as db:
            db.execute(
                """CREATE TABLE IF NOT EXISTS response_cache (
                    cache_key TEXT PRIMARY KEY,
                    body TEXT NOT NULL,
                    expires_at REAL NOT NULL,
                    stale_until REAL NOT NULL,
                    updated_at REAL NOT NULL
                )"""
            )

    def get(self, key: str, *, now: float | None = None) -> CacheHit | None:
        now = time.time() if now is None else now
        with self._connect() as db:
            row = db.execute(
                "SELECT body, expires_at, stale_until FROM response_cache WHERE cache_key = ?",
                (key,),
            ).fetchone()
        if not row or now > row[2]:
            return None
        return CacheHit(json.loads(row[0]), "fresh" if now <= row[1] else "stale")

    def put(
        self,
        key: str,
        value: dict[str, Any],
        *,
        ttl: int,
        stale_seconds: int,
        now: float | None = None,
    ) -> None:
        now = time.time() if now is None else now
        body = json.dumps(value, separators=(",", ":"), ensure_ascii=False)
        with self._connect() as db:
            db.execute(
                """INSERT INTO response_cache(cache_key, body, expires_at, stale_until, updated_at)
                   VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(cache_key) DO UPDATE SET
                     body=excluded.body, expires_at=excluded.expires_at,
                     stale_until=excluded.stale_until, updated_at=excluded.updated_at""",
                (key, body, now + ttl, now + ttl + stale_seconds, now),
            )

    def delete_expired(self, *, now: float | None = None) -> int:
        now = time.time() if now is None else now
        with self._connect() as db:
            cursor = db.execute("DELETE FROM response_cache WHERE stale_until < ?", (now,))
            return cursor.rowcount

    def writable(self) -> bool:
        try:
            with self._connect() as db:
                db.execute("SELECT 1")
            return True
        except sqlite3.Error:
            return False
