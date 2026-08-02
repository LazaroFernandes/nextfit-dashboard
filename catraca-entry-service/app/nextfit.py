from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests


class NextFitPresenceClient:
    def __init__(
        self,
        token: str,
        unit: str,
        refresh_token: str,
        token_path: Path,
        base_url: str,
    ):
        self.base_url = base_url
        self.unit = unit
        self.token_path = token_path
        persisted = self._read_tokens()
        self.token = str(persisted.get("access_token") or token)
        self.refresh_token = str(persisted.get("refresh_token") or refresh_token)
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "Authorization": f"Bearer {self.token}",
            "codigo-unidade": unit,
            "front-version": "1.1.5",
            "Origin": "https://app.nextfit.com.br",
            "Referer": "https://app.nextfit.com.br/",
            "User-Agent": "catraca-entry-service/1.0",
        })

    def _read_tokens(self) -> dict:
        if not self.token_path.exists():
            return {}
        try:
            return json.loads(self.token_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}

    def _save_tokens(self) -> None:
        self.token_path.parent.mkdir(parents=True, exist_ok=True)
        self.token_path.write_text(json.dumps({
            "access_token": self.token,
            "refresh_token": self.refresh_token,
        }), encoding="utf-8")

    def _refresh(self) -> bool:
        if not self.refresh_token:
            return False
        response = requests.post(
            f"{self.base_url}/api/Token",
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Authorization": f"Bearer {self.token}",
                "Origin": "https://app.nextfit.com.br",
                "Referer": "https://app.nextfit.com.br/",
            },
            data=(
                f"grant_type=refresh_token&refresh_token={self.refresh_token}"
                "&app_id=nextfit-sistema-academia"
            ),
            timeout=30,
        )
        if response.status_code != 200:
            return False
        payload = response.json()
        if not payload.get("access_token"):
            return False
        self.token = payload["access_token"]
        self.refresh_token = payload.get("refresh_token") or self.refresh_token
        self.session.headers["Authorization"] = f"Bearer {self.token}"
        self._save_tokens()
        return True

    def _get(self, path: str, params: dict[str, Any]) -> dict:
        response = self.session.get(f"{self.base_url}{path}", params=params, timeout=60)
        if response.status_code == 401 and self._refresh():
            response = self.session.get(f"{self.base_url}{path}", params=params, timeout=60)
        if response.status_code == 401:
            raise RuntimeError("Tokens do NextFit expirados; atualize as credenciais do serviço.")
        response.raise_for_status()
        return response.json()

    @staticmethod
    def _utc(value: datetime) -> str:
        return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")

    def presences(self, start: datetime, end: datetime) -> list[dict]:
        fields = json.dumps([
            "Id", "CodigoCliente", "NomeCliente", "DescricaoTipo", "Descricao", "Data",
        ])
        sort = json.dumps([{"direction": "DESC", "property": "Data"}])
        results: list[dict] = []
        page = 1
        while True:
            payload = self._get("/api/v2/RelCliente/RecuperarPresencas", {
                "limit": 100,
                "page": page,
                "fields": fields,
                "includes": "[]",
                "sort": sort,
                "DataInicial": self._utc(start),
                "DataFinal": self._utc(end),
                "ExibirClientesAgregadores": "true",
                "filter": "[]",
            })
            content = payload.get("Content") or []
            results.extend(content)
            if payload.get("Last") or not content:
                break
            page += 1
        return results
