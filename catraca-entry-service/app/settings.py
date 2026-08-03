from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    database_path: Path
    token_path: Path
    api_key: str
    nextfit_token: str
    nextfit_refresh_token: str
    nextfit_unit: str
    nextfit_base_url: str
    media_entry_url: str
    media_entry_api_key: str
    media_unit_id: str
    poll_seconds: int
    overlap_seconds: int
    bootstrap_lookback_minutes: int
    retention_days: int

    @classmethod
    def from_env(cls) -> "Settings":
        data_dir = Path(os.environ.get("CATRACA_DATA_DIR", "data"))
        return cls(
            database_path=Path(os.environ.get("CATRACA_DATABASE_PATH", data_dir / "entries.db")),
            token_path=Path(os.environ.get("CATRACA_TOKEN_PATH", data_dir / "nextfit-tokens.json")),
            api_key=os.environ.get("CATRACA_API_KEY", "").strip(),
            nextfit_token=os.environ.get("NEXTFIT_V2_TOKEN", "").strip(),
            nextfit_refresh_token=os.environ.get("NEXTFIT_V2_REFRESH_TOKEN", "").strip(),
            nextfit_unit=os.environ.get("NEXTFIT_CODIGO_UNIDADE", "").strip(),
            nextfit_base_url=os.environ.get("NEXTFIT_V2_BASE_URL", "https://api.nextfit.com.br").rstrip("/"),
            media_entry_url=os.environ.get("MIDIA_ENTRY_URL", "").strip(),
            media_entry_api_key=os.environ.get("MIDIA_ENTRY_API_KEY", "").strip(),
            media_unit_id=os.environ.get("MIDIA_UNIT_ID", "").strip(),
            poll_seconds=max(5, int(os.environ.get("CATRACA_POLL_SECONDS", "15"))),
            overlap_seconds=max(0, int(os.environ.get("CATRACA_OVERLAP_SECONDS", "120"))),
            bootstrap_lookback_minutes=max(1, int(os.environ.get("CATRACA_BOOTSTRAP_LOOKBACK_MINUTES", "10"))),
            retention_days=max(1, int(os.environ.get("CATRACA_RETENTION_DAYS", "7"))),
        )

    @property
    def nextfit_configured(self) -> bool:
        return bool(self.nextfit_token and self.nextfit_unit)

    @property
    def media_configured(self) -> bool:
        return bool(self.media_entry_url and self.media_entry_api_key and self.media_unit_id)
