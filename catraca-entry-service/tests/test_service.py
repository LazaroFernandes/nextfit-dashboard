from __future__ import annotations

import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient

from app.main import EntryService, create_app
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


if __name__ == "__main__":
    unittest.main()
