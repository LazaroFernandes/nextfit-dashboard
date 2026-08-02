from __future__ import annotations

import asyncio
import logging
import secrets
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

from fastapi import Depends, FastAPI, Header, HTTPException, Query

from .nextfit import NextFitPresenceClient
from .settings import Settings
from .store import EntryStore, TIMEZONE, parse_datetime


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("catraca.entry")


class EntryService:
    def __init__(self, settings: Settings, store: EntryStore, client=None):
        self.settings = settings
        self.store = store
        self.client = client
        self.last_sync_at: str | None = None
        self.last_error: str | None = None

    def poll_once(self, now: datetime | None = None) -> int:
        if self.client is None:
            raise RuntimeError("Integração com o NextFit não configurada.")
        now = now or datetime.now(TIMEZONE)
        last_poll = parse_datetime(self.store.state("last_poll"))
        start = (
            last_poll - timedelta(seconds=self.settings.overlap_seconds)
            if last_poll
            else now - timedelta(minutes=self.settings.bootstrap_lookback_minutes)
        )
        rows = self.client.presences(start, now)
        inserted = self.store.ingest(rows, now)
        self.store.set_state("last_poll", now.isoformat())
        self.store.cleanup_before(now - timedelta(days=self.settings.retention_days))
        self.last_sync_at = now.isoformat()
        self.last_error = None
        if inserted:
            logger.info("%s nova(s) entrada(s) detectada(s)", inserted)
        return inserted

    async def run(self, stop: asyncio.Event) -> None:
        while not stop.is_set():
            try:
                await asyncio.to_thread(self.poll_once)
            except Exception as exc:
                self.last_error = str(exc).splitlines()[0]
                logger.error("Falha ao consultar o NextFit: %s", self.last_error)
            try:
                await asyncio.wait_for(stop.wait(), timeout=self.settings.poll_seconds)
            except TimeoutError:
                pass


def create_app(settings: Settings | None = None, store: EntryStore | None = None, client=None) -> FastAPI:
    settings = settings or Settings.from_env()
    store = store or EntryStore(settings.database_path)
    if client is None and settings.nextfit_configured:
        client = NextFitPresenceClient(
            token=settings.nextfit_token,
            unit=settings.nextfit_unit,
            refresh_token=settings.nextfit_refresh_token,
            token_path=settings.token_path,
            base_url=settings.nextfit_base_url,
        )
    service = EntryService(settings, store, client)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        stop = asyncio.Event()
        task = asyncio.create_task(service.run(stop)) if service.client else None
        yield
        stop.set()
        if task:
            await task

    app = FastAPI(
        title="Catraca Entry Service",
        version="1.0.0",
        description="Detecta e disponibiliza entradas da catraca registradas no NextFit.",
        lifespan=lifespan,
    )
    app.state.entry_service = service

    def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
        if not settings.api_key:
            raise HTTPException(status_code=503, detail="CATRACA_API_KEY não configurada")
        if not x_api_key or not secrets.compare_digest(x_api_key, settings.api_key):
            raise HTTPException(status_code=401, detail="API Key inválida")

    @app.get("/health")
    def health() -> dict:
        configured = bool(service.client and settings.api_key)
        return {
            "status": "ok" if configured and not service.last_error else "degraded",
            "service": "catraca-entry-service",
            "nextfit_configured": bool(service.client),
            "api_key_configured": bool(settings.api_key),
            "last_sync_at": service.last_sync_at,
            "last_error": service.last_error,
            "stored_events": store.count(),
            "poll_seconds": settings.poll_seconds,
        }

    @app.get("/v1/entries", dependencies=[Depends(require_api_key)])
    def entries(
        after: int = Query(default=0, ge=0),
        limit: int = Query(default=100, ge=1, le=500),
    ) -> dict:
        items = store.list_after(after, limit)
        return {
            "items": items,
            "next_cursor": items[-1]["id"] if items else after,
            "has_more": len(items) == limit,
        }

    @app.get("/v1/entries/latest", dependencies=[Depends(require_api_key)])
    def latest() -> dict:
        return {"item": store.latest()}

    return app


app = create_app()
