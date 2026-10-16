"""File d'envoi locale pour synchroniser les mesures Mac vers Node-RED."""
from __future__ import annotations

import json
import sqlite3
import threading
import time
import urllib.error
import urllib.request
from contextlib import contextmanager
from pathlib import Path
from typing import Any


class SyncOutbox:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute(
                "CREATE TABLE IF NOT EXISTS pending_measurements ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT, payload TEXT NOT NULL)"
            )

    @contextmanager
    def _connect(self):
        connection = sqlite3.connect(self.path, timeout=5)
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def enqueue(self, payload: dict[str, Any]) -> int:
        with self._connect() as connection:
            cursor = connection.execute(
                "INSERT INTO pending_measurements(payload) VALUES (?)",
                (json.dumps(payload, separators=(",", ":"), allow_nan=False),),
            )
            return int(cursor.lastrowid)

    def pending(self, limit: int = 50) -> list[tuple[int, dict[str, Any]]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT id, payload FROM pending_measurements ORDER BY id LIMIT ?",
                (limit,),
            ).fetchall()
        return [(row_id, json.loads(payload)) for row_id, payload in rows]

    def acknowledge(self, row_ids: list[int]) -> None:
        if not row_ids:
            return
        placeholders = ",".join("?" for _ in row_ids)
        with self._connect() as connection:
            connection.execute(
                f"DELETE FROM pending_measurements WHERE id IN ({placeholders})",
                row_ids,
            )

    def count(self) -> int:
        with self._connect() as connection:
            return int(connection.execute(
                "SELECT COUNT(*) FROM pending_measurements"
            ).fetchone()[0])


def send_measurement(endpoint: str, payload: dict[str, Any], timeout: float = 2.0) -> None:
    request = urllib.request.Request(
        endpoint,
        data=json.dumps(payload, separators=(",", ":"), allow_nan=False).encode(),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        if not 200 <= response.status < 300:
            raise urllib.error.HTTPError(
                endpoint, response.status, "Node-RED refused measurement", response.headers, None
            )


class SyncWorker(threading.Thread):
    def __init__(self, outbox: SyncOutbox, endpoint: str, events):
        super().__init__(daemon=True)
        self.outbox = outbox
        self.endpoint = endpoint
        self.events = events
        self.stop_flag = threading.Event()

    def run(self):
        while not self.stop_flag.is_set():
            batch = self.outbox.pending()
            if not batch:
                self.stop_flag.wait(1)
                continue
            row_ids = [row_id for row_id, _ in batch]
            try:
                for _, payload in batch:
                    send_measurement(self.endpoint, payload)
                self.outbox.acknowledge(row_ids)
                self.events.put(("sync_ok", self.outbox.count()))
            except (OSError, ValueError, urllib.error.URLError) as error:
                self.events.put(("sync_error", str(error), self.outbox.count()))
                self.stop_flag.wait(10)
