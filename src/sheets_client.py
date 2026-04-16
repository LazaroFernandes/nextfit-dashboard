"""Escreve listas de dicionários em abas de uma planilha do Google Sheets.

Cada chamada a `write_tab` substitui o conteúdo da aba inteiramente — a ideia é
que o sync seja idempotente: rodou, estado da planilha reflete estado da API.
"""
from __future__ import annotations

from typing import Any

import gspread
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def _flatten(value: Any) -> Any:
    """Converte valores aninhados (listas/dicts) em string pra caber numa célula."""
    if value is None:
        return ""
    if isinstance(value, (list, dict)):
        import json
        return json.dumps(value, ensure_ascii=False, default=str)
    if isinstance(value, bool):
        return "VERDADEIRO" if value else "FALSO"
    return value


def _rows_from_items(items: list[dict[str, Any]]) -> tuple[list[str], list[list[Any]]]:
    """Extrai cabeçalho (união de todas as chaves) e as linhas."""
    if not items:
        return [], []
    headers: list[str] = []
    seen: set[str] = set()
    for item in items:
        for key in item.keys():
            if key not in seen:
                seen.add(key)
                headers.append(key)
    rows = [[_flatten(item.get(h)) for h in headers] for item in items]
    return headers, rows


class SheetsClient:
    def __init__(
        self,
        credentials_file: str | None = None,
        sheet_id: str = "",
        *,
        credentials_info: dict[str, Any] | None = None,
    ):
        if credentials_info is not None:
            creds = Credentials.from_service_account_info(credentials_info, scopes=SCOPES)
        elif credentials_file is not None:
            creds = Credentials.from_service_account_file(credentials_file, scopes=SCOPES)
        else:
            raise ValueError("Informe credentials_file ou credentials_info")
        self.gc = gspread.authorize(creds)
        self.spreadsheet = self.gc.open_by_key(sheet_id)

    def _get_or_create_worksheet(self, title: str, rows: int, cols: int) -> gspread.Worksheet:
        try:
            return self.spreadsheet.worksheet(title)
        except gspread.WorksheetNotFound:
            return self.spreadsheet.add_worksheet(title=title, rows=max(rows, 100), cols=max(cols, 26))

    def write_tab(self, tab_name: str, items: list[dict[str, Any]]) -> int:
        """Substitui o conteúdo da aba `tab_name` pelos `items`. Retorna contagem escrita."""
        headers, rows = _rows_from_items(items)
        if not headers:
            # Sem dados: apenas limpa a aba (se existir) e escreve um aviso
            ws = self._get_or_create_worksheet(tab_name, rows=2, cols=1)
            ws.clear()
            ws.update(values=[["(sem registros)"]], range_name="A1")
            return 0

        ws = self._get_or_create_worksheet(tab_name, rows=len(rows) + 10, cols=len(headers))
        ws.clear()
        payload = [headers, *rows]
        ws.update(values=payload, range_name="A1")
        # Formata o cabeçalho em negrito
        try:
            ws.format("1:1", {"textFormat": {"bold": True}})
        except Exception:
            pass  # formatação é cosmética, não falha o sync
        return len(rows)

    def append_tab(self, tab_name: str, items: list[dict[str, Any]]) -> int:
        """Adiciona linhas ao final da aba `tab_name` sem sobrescrever dados existentes.

        Se a aba não existir, cria com cabeçalho. Se existir, adiciona apenas
        as linhas novas usando o cabeçalho já presente na aba.
        Retorna a quantidade de linhas adicionadas.
        """
        headers, rows = _rows_from_items(items)
        if not headers or not rows:
            return 0

        needed_rows = len(rows) + 10
        ws = self._get_or_create_worksheet(tab_name, rows=needed_rows, cols=len(headers))
        existing = ws.get_all_values()

        if not existing or not existing[0]:
            # Aba vazia — escreve cabeçalho + dados
            total_rows = len(rows) + 1
            if ws.row_count < total_rows:
                ws.resize(rows=total_rows + 100, cols=len(headers))
            ws.update(values=[headers], range_name="A1")
            # Escreve dados em lotes de 1000 linhas
            self._batch_update(ws, rows, start_row=2)
            try:
                ws.format("1:1", {"textFormat": {"bold": True}})
            except Exception:
                pass
            return len(rows)

        # Aba já tem dados — usa o cabeçalho existente para manter a ordem das colunas
        existing_headers = existing[0]
        reordered_rows = []
        for item in items:
            reordered_rows.append([_flatten(item.get(h)) for h in existing_headers])

        next_row = len(existing) + 1
        total_needed = next_row + len(reordered_rows)
        if ws.row_count < total_needed:
            ws.resize(rows=total_needed + 100, cols=len(existing_headers))
        self._batch_update(ws, reordered_rows, start_row=next_row)
        return len(reordered_rows)

    @staticmethod
    def _batch_update(ws: gspread.Worksheet, rows: list[list[Any]], start_row: int, batch_size: int = 1000) -> None:
        """Escreve linhas em lotes para evitar limites da API do Sheets."""
        for i in range(0, len(rows), batch_size):
            batch = rows[i:i + batch_size]
            row_num = start_row + i
            ws.update(values=batch, range_name=f"A{row_num}")

    def read_tab_column(self, tab_name: str, col_index: int) -> list[str]:
        """Lê todos os valores de uma coluna (0-indexed) da aba. Retorna lista vazia se a aba não existir."""
        try:
            ws = self.spreadsheet.worksheet(tab_name)
        except gspread.WorksheetNotFound:
            return []
        values = ws.col_values(col_index + 1)  # gspread usa 1-indexed
        return values[1:]  # pula o cabeçalho
