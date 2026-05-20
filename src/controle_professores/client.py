"""Helpers para abrir a planilha 'Controle Professores' em qualquer script.

Centraliza a leitura do .env e a criacao do SheetsClient apontando para a
planilha nova (separada do GOOGLE_SHEET_ID que e a do sync NextFit).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))

from controle_professores.config import ENV_SHEET_ID  # noqa: E402
from sheets_client import SheetsClient  # noqa: E402


def load_env() -> None:
    load_dotenv(PROJECT_ROOT / ".env")


def get_sheet_id() -> str:
    load_env()
    sid = os.environ.get(ENV_SHEET_ID, "").strip()
    if not sid:
        raise RuntimeError(
            f"{ENV_SHEET_ID} nao definida no .env. "
            f"Rode 'python -m controle_professores.setup' primeiro."
        )
    return sid


def get_creds_path() -> Path:
    creds_file = os.environ.get("GOOGLE_CREDENTIALS_FILE", "credentials/service-account.json")
    p = Path(creds_file)
    if not p.is_absolute():
        p = PROJECT_ROOT / p
    return p


def _st_secrets() -> dict | None:
    """Retorna st.secrets se rodando sob Streamlit com secrets configurados.

    Em produção (Streamlit Community Cloud) as credenciais vêm daqui; localmente,
    sem secrets.toml, retorna None e o codigo cai pro .env + arquivo local.
    """
    try:
        import streamlit as st

        # Acessar st.secrets sem secrets.toml lanca excecao — por isso o try.
        if "gcp_service_account" in st.secrets:
            return st.secrets
    except Exception:
        pass
    return None


def _open(sheet_id_env: str) -> SheetsClient:
    """Abre uma planilha pelo nome da variavel que guarda seu id.

    Prioriza st.secrets (prod); cai pro .env + credentials/service-account.json (dev).
    """
    secrets = _st_secrets()
    if secrets is not None:
        # ID da planilha: primeiro nos secrets; se ausente, cai pro .env. Assim um
        # secrets.toml local que só tem as credenciais continua funcionando.
        sid = str(secrets.get(sheet_id_env) or "").strip()
        if not sid:
            load_env()
            sid = os.environ.get(sheet_id_env, "").strip()
        if not sid:
            raise RuntimeError(f"{sheet_id_env} nao definida nos Secrets nem no .env.")
        return SheetsClient(
            credentials_info=dict(secrets["gcp_service_account"]),
            sheet_id=sid,
        )
    load_env()
    sid = os.environ.get(sheet_id_env, "").strip()
    if not sid:
        raise RuntimeError(f"{sheet_id_env} nao definida no .env")
    return SheetsClient(credentials_file=str(get_creds_path()), sheet_id=sid)


def open_controle() -> SheetsClient:
    """Abre a planilha 'Controle Professores'."""
    return _open(ENV_SHEET_ID)


def open_nextfit_sync() -> SheetsClient:
    """Abre a planilha do sync NextFit (a antiga, com Clientes/Presencas/etc.)."""
    return _open("GOOGLE_SHEET_ID")


def read_config() -> dict[str, str]:
    """Le a aba Config como dict {chave: valor}."""
    from controle_professores.config import TAB_CONFIG
    sc = open_controle()
    rows = sc.read_tab_all(TAB_CONFIG)
    out: dict[str, str] = {}
    for r in rows:
        k = str(r.get("Chave") or "").strip()
        v = str(r.get("Valor") or "").strip()
        if k:
            out[k] = v
    return out


def get_config_int(chave: str, default: int) -> int:
    cfg = read_config()
    raw = cfg.get(chave, "").strip()
    try:
        return int(raw) if raw else default
    except ValueError:
        return default
