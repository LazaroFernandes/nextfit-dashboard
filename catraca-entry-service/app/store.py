from __future__ import annotations

import hashlib
import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


TIMEZONE = ZoneInfo("America/Sao_Paulo")


def parse_datetime(value: object) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=TIMEZONE)
    return parsed.astimezone(TIMEZONE)


def event_key(row: dict) -> str:
    if row.get("Id") is not None:
        return f"nextfit:{row['Id']}"
    raw = "|".join(str(row.get(field) or "") for field in (
        "CodigoCliente", "Data", "DescricaoTipo", "Descricao", "NomeCliente",
    ))
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


class EntryStore:
    def __init__(self, path: Path, delivery_enabled: bool = False):
        self.path = path
        self.delivery_enabled = delivery_enabled
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=30)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with closing(self._connect()) as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            with connection:
                connection.execute("""
                    CREATE TABLE IF NOT EXISTS entry_events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        event_key TEXT NOT NULL UNIQUE,
                        student_id TEXT NOT NULL,
                        student_name TEXT NOT NULL,
                        entered_at TEXT NOT NULL,
                        received_at TEXT NOT NULL,
                        delivered_at TEXT
                    )
                """)
                columns = {
                    row[1] for row in connection.execute("PRAGMA table_info(entry_events)")
                }
                if "delivered_at" not in columns:
                    connection.execute("ALTER TABLE entry_events ADD COLUMN delivered_at TEXT")
                    connection.execute(
                        "UPDATE entry_events SET delivered_at = received_at WHERE delivered_at IS NULL"
                    )
                connection.execute("""
                    CREATE TABLE IF NOT EXISTS service_state (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL
                    )
                """)

    def ingest(self, rows: list[dict], received_at: datetime) -> int:
        inserted = 0
        with closing(self._connect()) as connection:
            with connection:
                for row in rows:
                    if str(row.get("DescricaoTipo") or "").strip().casefold() != "acesso":
                        continue
                    entered_at = parse_datetime(row.get("Data"))
                    student_id = str(row.get("CodigoCliente") or "").strip()
                    name = str(row.get("NomeCliente") or "").strip()
                    if not entered_at or not student_id or not name:
                        continue
                    cursor = connection.execute(
                        """
                        INSERT OR IGNORE INTO entry_events
                            (event_key, student_id, student_name, entered_at, received_at, delivered_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            event_key(row),
                            student_id,
                            name,
                            entered_at.isoformat(),
                            received_at.isoformat(),
                            None if self.delivery_enabled else received_at.isoformat(),
                        ),
                    )
                    inserted += cursor.rowcount
        return inserted

    def list_after(self, cursor: int, limit: int) -> list[dict]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT id, student_id, student_name, entered_at, received_at
                FROM entry_events WHERE id > ? ORDER BY id ASC LIMIT ?
                """,
                (cursor, limit),
            ).fetchall()
        return [dict(row) for row in rows]

    def latest(self) -> dict | None:
        with closing(self._connect()) as connection:
            row = connection.execute(
                """
                SELECT id, student_id, student_name, entered_at, received_at
                FROM entry_events ORDER BY id DESC LIMIT 1
                """
            ).fetchone()
        return dict(row) if row else None

    def pending_deliveries(self, limit: int = 100) -> list[dict]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT id, student_id, student_name, entered_at, received_at
                FROM entry_events
                WHERE delivered_at IS NULL
                ORDER BY id ASC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def mark_delivered(self, entry_id: int, delivered_at: datetime) -> None:
        with closing(self._connect()) as connection:
            with connection:
                connection.execute(
                    "UPDATE entry_events SET delivered_at = ? WHERE id = ?",
                    (delivered_at.isoformat(), entry_id),
                )

    def pending_count(self) -> int:
        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT COUNT(*) AS total FROM entry_events WHERE delivered_at IS NULL"
            ).fetchone()
        return int(row["total"])

    def count(self) -> int:
        with closing(self._connect()) as connection:
            row = connection.execute("SELECT COUNT(*) AS total FROM entry_events").fetchone()
        return int(row["total"])

    def cleanup_before(self, cutoff: datetime) -> int:
        with closing(self._connect()) as connection:
            with connection:
                cursor = connection.execute(
                    "DELETE FROM entry_events WHERE entered_at < ?",
                    (cutoff.isoformat(),),
                )
        return cursor.rowcount

    def state(self, key: str) -> str | None:
        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT value FROM service_state WHERE key = ?", (key,)
            ).fetchone()
        return str(row["value"]) if row else None

    def set_state(self, key: str, value: str) -> None:
        with closing(self._connect()) as connection:
            with connection:
                connection.execute(
                    """
                    INSERT INTO service_state (key, value) VALUES (?, ?)
                    ON CONFLICT(key) DO UPDATE SET value = excluded.value
                    """,
                    (key, value),
                )
