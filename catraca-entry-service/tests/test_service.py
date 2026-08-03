from __future__ import annotations

import sqlite3
import tempfile
import unittest
from contextlib import closing
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient

from app.main import EntryService, create_app
from app.media import MediaEntryClient
from app.settings import Settings
from app.store import EntryStore


TZ = ZoneInfo("America/Sao_Paulo")


def settings_for(path: Path) -> Settings:
    return Settings(
        database_path=path / "entries.db",
        token_path=path / "tokens.json",
        api_key="test-key",
        nextfit_token="token",
        nextfit_refresh_token="refresh",
        nextfit_unit="16173",
        nextfit_base_url="https://api.nextfit.com.br",
        media_entry_url="",
        media_entry_api_key="",
        media_unit_id="",
        poll_seconds=15,
        overlap_seconds=120,
        bootstrap_lookback_minutes=10,
        retention_days=7,
    )


class FakeNextFit:
    def __init__(self, rows: list[dict]):
        self.rows = rows

    def presences(self, _start, _end) -> list[dict]:
        return self.rows


class FakeMedia:
    def __init__(self, error: Exception | None = None):
        self.error = error
        self.entries: list[dict] = []

    def send(self, entry: dict) -> None:
        if self.error:
            raise self.error
        self.entries.append(entry)


class FakeResponse:
    status_code = 201


class FakeSession:
    def __init__(self):
        self.call: dict | None = None

    def post(self, url, **kwargs):
        self.call = {"url": url, **kwargs}
        return FakeResponse()


class EntryServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name)
        self.settings = settings_for(self.path)
        self.store = EntryStore(self.settings.database_path)
        self.rows = [
            {
                "Id": 1,
                "CodigoCliente": 10,
                "NomeCliente": "Ana",
                "DescricaoTipo": "Acesso",
                "Data": "2026-08-01T10:00:00-03:00",
            },
            {
                "Id": 2,
                "CodigoCliente": 20,
                "NomeCliente": "Bruno",
                "DescricaoTipo": "Agenda",
                "Data": "2026-08-01T10:05:00-03:00",
            },
        ]

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_poll_keeps_only_access_and_deduplicates(self) -> None:
        service = EntryService(self.settings, self.store, FakeNextFit(self.rows))
        now = datetime(2026, 8, 1, 10, 10, tzinfo=TZ)

        self.assertEqual(service.poll_once(now), 1)
        self.assertEqual(service.poll_once(now), 0)
        self.assertEqual(self.store.count(), 1)
        self.assertEqual(self.store.latest()["student_name"], "Ana")

    def test_entries_endpoint_requires_key_and_returns_cursor(self) -> None:
        self.store.ingest(self.rows, datetime(2026, 8, 1, 10, 10, tzinfo=TZ))
        app = create_app(self.settings, self.store, FakeNextFit([]))

        with TestClient(app) as client:
            self.assertEqual(client.get("/v1/entries").status_code, 401)
            response = client.get("/v1/entries", headers={"X-Api-Key": "test-key"})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload["items"]), 1)
        self.assertEqual(payload["next_cursor"], payload["items"][0]["id"])

    def test_new_entry_is_delivered_and_marked(self) -> None:
        store = EntryStore(self.settings.database_path, delivery_enabled=True)
        media = FakeMedia()
        service = EntryService(self.settings, store, FakeNextFit(self.rows), media)
        now = datetime(2026, 8, 1, 10, 10, tzinfo=TZ)

        self.assertEqual(service.poll_once(now), 1)
        self.assertEqual(store.pending_count(), 1)
        self.assertEqual(service.deliver_pending(), 1)
        self.assertEqual(store.pending_count(), 0)
        self.assertEqual(media.entries[0]["student_name"], "Ana")

    def test_failed_delivery_remains_pending_for_retry(self) -> None:
        store = EntryStore(self.settings.database_path, delivery_enabled=True)
        store.ingest(self.rows, datetime(2026, 8, 1, 10, 10, tzinfo=TZ))
        failing = EntryService(
            self.settings,
            store,
            FakeNextFit([]),
            FakeMedia(RuntimeError("offline")),
        )

        with self.assertRaisesRegex(RuntimeError, "offline"):
            failing.deliver_pending()
        self.assertEqual(store.pending_count(), 1)

        recovered = EntryService(self.settings, store, FakeNextFit([]), FakeMedia())
        self.assertEqual(recovered.deliver_pending(), 1)
        self.assertEqual(store.pending_count(), 0)

    def test_events_created_without_integration_are_not_sent_later(self) -> None:
        disabled = EntryStore(self.settings.database_path)
        disabled.ingest(self.rows, datetime(2026, 8, 1, 10, 10, tzinfo=TZ))

        enabled = EntryStore(self.settings.database_path, delivery_enabled=True)

        self.assertEqual(enabled.pending_count(), 0)

    def test_legacy_database_marks_existing_events_as_delivered(self) -> None:
        legacy_path = self.path / "legacy.db"
        with closing(sqlite3.connect(legacy_path)) as connection:
            connection.execute(
                """
                CREATE TABLE entry_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_key TEXT NOT NULL UNIQUE,
                    student_id TEXT NOT NULL,
                    student_name TEXT NOT NULL,
                    entered_at TEXT NOT NULL,
                    received_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                INSERT INTO entry_events
                    (event_key, student_id, student_name, entered_at, received_at)
                VALUES ('old:1', '10', 'Ana', '2026-08-01T10:00:00-03:00', '2026-08-01T10:00:01-03:00')
                """
            )
            connection.commit()

        migrated = EntryStore(legacy_path, delivery_enabled=True)

        self.assertEqual(migrated.count(), 1)
        self.assertEqual(migrated.pending_count(), 0)

    def test_media_client_sends_expected_contract(self) -> None:
        client = MediaEntryClient("https://midia.example/api/entry", "secret", "unit-1")
        session = FakeSession()
        client.session = session

        client.send({
            "student_id": "10",
            "student_name": "Ana Silva",
            "entered_at": "2026-08-01T10:00:00-03:00",
        })

        self.assertEqual(session.call["headers"], {"X-Api-Key": "secret"})
        self.assertEqual(session.call["json"], {
            "studentId": "10",
            "name": "Ana Silva",
            "enteredAt": "2026-08-01T10:00:00-03:00",
            "unitId": "unit-1",
        })


if __name__ == "__main__":
    unittest.main()
