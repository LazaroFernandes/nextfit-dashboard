"""Cliente da API interna v2 do NextFit (api.nextfit.com.br).

Esta API é a usada pelo painel web (app.nextfit.com.br), não é a API pública
de integração. Autenticação é via JWT Bearer de curta duração (~10h).

O token pode ser renovado automaticamente usando o refresh token (5 dias).
Quando o refresh token também expirar, o usuário precisa fazer login
manualmente no app.nextfit.com.br e extrair novos tokens via DevTools.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests


class TokenExpiredError(RuntimeError):
    """Levantado quando o JWT v2 expirou e não foi possível renovar."""


class NextFitV2Client:
    def __init__(
        self,
        token: str,
        codigo_unidade: str | int,
        refresh_token: str | None = None,
        env_path: Path | None = None,
        base_url: str = "https://api.nextfit.com.br",
        front_version: str = "1.1.5",
        page_size: int = 30,
    ):
        self.base_url = base_url.rstrip("/")
        self.page_size = page_size
        self.refresh_token = refresh_token
        self.env_path = env_path
        self._token = token
        self._codigo_unidade = str(codigo_unidade)
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
            "codigo-unidade": self._codigo_unidade,
            "front-version": front_version,
            "Origin": "https://app.nextfit.com.br",
            "Referer": "https://app.nextfit.com.br/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        })

    def _refresh_access_token(self) -> bool:
        """Tenta renovar o access token usando o refresh token.

        Retorna True se conseguiu renovar, False caso contrário.
        Também atualiza o .env com os novos tokens.
        """
        if not self.refresh_token:
            return False

        resp = requests.post(
            f"{self.base_url}/api/Token",
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Authorization": f"Bearer {self._token}",
                "Origin": "https://app.nextfit.com.br",
                "Referer": "https://app.nextfit.com.br/",
            },
            data=f"grant_type=refresh_token&refresh_token={self.refresh_token}"
                 f"&app_id=nextfit-sistema-academia",
            timeout=30,
        )
        if resp.status_code != 200:
            return False

        data = resp.json()
        new_access = data.get("access_token")
        new_refresh = data.get("refresh_token")
        if not new_access:
            return False

        # Atualiza sessão com novo token
        self._token = new_access
        self.session.headers["Authorization"] = f"Bearer {new_access}"

        if new_refresh:
            self.refresh_token = new_refresh

        # Persiste novos tokens no .env
        self._update_env_tokens(new_access, new_refresh)
        return True

    def _update_env_tokens(self, access_token: str, refresh_token: str | None) -> None:
        """Atualiza os tokens no arquivo .env para que fiquem válidos na próxima execução."""
        if not self.env_path or not self.env_path.exists():
            return
        content = self.env_path.read_text(encoding="utf-8")
        new_lines = []
        for line in content.splitlines():
            if line.startswith("NEXTFIT_V2_TOKEN="):
                new_lines.append(f"NEXTFIT_V2_TOKEN={access_token}")
            elif refresh_token and line.startswith("NEXTFIT_V2_REFRESH_TOKEN="):
                new_lines.append(f"NEXTFIT_V2_REFRESH_TOKEN={refresh_token}")
            else:
                new_lines.append(line)
        self.env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")

    def _get(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        resp = self.session.get(url, params=params, timeout=60)
        if resp.status_code == 401:
            if self._refresh_access_token():
                print("[token] access token renovado automaticamente via refresh token")
                resp = self.session.get(url, params=params, timeout=60)
            if resp.status_code == 401:
                raise TokenExpiredError(
                    "Token v2 expirado e refresh token tambem expirou.\n"
                    "  1) Entre em https://app.nextfit.com.br\n"
                    "  2) F12 -> Console -> execute:\n"
                    "     localStorage.getItem('X-REFRESH-TOKEN')\n"
                    "  3) Cole o valor em NEXTFIT_V2_REFRESH_TOKEN no .env\n"
                    "  4) Copie tambem o header Authorization de qualquer request\n"
                    "     e cole em NEXTFIT_V2_TOKEN no .env"
                )
        if not resp.ok:
            body = resp.text[:500] if resp.text else "(vazio)"
            raise RuntimeError(f"HTTP {resp.status_code} em {resp.url}\n  corpo: {body}")
        return resp.json()

    @staticmethod
    def _fmt_utc(dt: datetime, end_of_day: bool = False) -> str:
        """Formata datetime em ISO UTC como o painel faz: 2026-04-01T03:00:00.000Z"""
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        dt_utc = dt.astimezone(timezone.utc)
        millis = "999" if end_of_day else "000"
        return dt_utc.strftime(f"%Y-%m-%dT%H:%M:%S.{millis}Z")

    def presencas(self, data_inicial: datetime, data_final: datetime) -> list[dict[str, Any]]:
        """Lista todas as presenças (Acesso + Agenda) no período informado.

        `data_inicial` e `data_final` podem ser datetimes naive (assumidos como
        horário local do sistema) ou tz-aware. São convertidos pra UTC.
        """
        fields = json.dumps([
            "Id", "Descricao", "Inativo", "NomeCliente",
            "DescricaoModalidade", "DescricaoContrato", "DescricaoTipo",
            "Data", "DddCliente",
        ])
        sort = json.dumps([{"direction": "DESC", "property": "Data"}])
        di = self._fmt_utc(data_inicial, end_of_day=False)
        df = self._fmt_utc(data_final, end_of_day=True)

        results: list[dict[str, Any]] = []
        page = 1
        while True:
            params = {
                "limit": self.page_size,
                "page": page,
                "fields": fields,
                "includes": "[]",
                "sort": sort,
                "DataInicial": di,
                "DataFinal": df,
                "ExibirClientesAgregadores": "true",
                "filter": "[]",
            }
            data = self._get("/api/v2/RelCliente/RecuperarPresencas", params)
            content = data.get("Content") or []
            results.extend(content)
            if data.get("Last") or not content:
                break
            page += 1
        return results

    # --- Grupos Musculares ---

    def grupos_exercicio(self) -> dict[int, str]:
        """Retorna mapeamento CodigoGrupoExercicio -> Nome do grupo muscular."""
        data = self._get("/api/GrupoExercicio", {"limit": 100, "page": 1})
        grupos = data.get("Content") or []
        return {g["Id"]: g.get("Descricao") or "" for g in grupos}

    # --- Treinos ---

    def listar_treinos(
        self, clientes_ativos: set[int] | None = None,
    ) -> list[dict[str, Any]]:
        """Lista treinos da unidade (relatório resumido via /api/v2/).

        Se `clientes_ativos` for fornecido, retorna apenas treinos
        de clientes cujo código está nesse conjunto.
        """
        fields = json.dumps([
            "Id", "CodigoCliente", "NomeCliente", "NomeUsuario",
            "Status", "DataCriacao", "QtdeUtilizado",
        ])
        sort = json.dumps([{"direction": "DESC", "property": "DataCriacao"}])

        results: list[dict[str, Any]] = []
        page = 1
        while True:
            params = {
                "limit": self.page_size,
                "page": page,
                "fields": fields,
                "sort": sort,
                "filter": "[]",
            }
            data = self._get("/api/v2/RelTreino/RecuperarRelTreino", params)
            content = data.get("Content") or []
            if clientes_ativos is not None:
                content = [t for t in content if t.get("CodigoCliente") in clientes_ativos]
            results.extend(content)
            if data.get("Last") or not content:
                break
            page += 1
        return results

    def detalhe_treino(self, treino_id: int) -> dict[str, Any]:
        """Recupera o treino completo (sessões + exercícios) via /api/."""
        data = self._get("/api/Treino/RecuperarView", {"Codigo": treino_id})
        return data.get("Content") or {}

    def _build_treino_rows(
        self,
        resumos: list[dict[str, Any]],
        grupos_map: dict[int, str],
        data_captura: str,
    ) -> list[dict[str, Any]]:
        """Constrói linhas achatadas (1 por exercício) a partir dos resumos de treinos."""
        rows: list[dict[str, Any]] = []

        for resumo in resumos:
            treino_id = resumo["Id"]
            detalhe = self.detalhe_treino(treino_id)
            if not detalhe:
                continue

            treino_nome = detalhe.get("Nome") or ""
            treino_obs = detalhe.get("Observacao") or ""
            cliente_nome = (detalhe.get("Cliente") or {}).get("Nome") or resumo.get("NomeCliente") or ""
            codigo_cliente = detalhe.get("CodigoCliente") or resumo.get("CodigoCliente")
            professor = (detalhe.get("Usuario") or {}).get("Nome") or resumo.get("NomeUsuario") or ""
            status = detalhe.get("Status")
            freq_semanal = detalhe.get("FrequenciaSemanal")
            data_criacao = detalhe.get("DataCriacao") or ""
            data_alteracao = detalhe.get("DataAlteracao") or ""
            qtde_utilizado = resumo.get("QtdeUtilizado", 0)

            sessoes = detalhe.get("Sessoes") or []
            for idx_sessao, sessao in enumerate(sessoes, 1):
                exercicios = sessao.get("Exercicios") or []
                for ex in exercicios:
                    ex_info = ex.get("Exercicio") or {}
                    codigo_grupo = ex_info.get("CodigoGrupoExercicio")
                    grupo_nome = grupos_map.get(codigo_grupo, "") if codigo_grupo else ""
                    rows.append({
                        "DataCaptura": data_captura,
                        "CodigoCliente": codigo_cliente,
                        "NomeCliente": cliente_nome,
                        "Professor": professor,
                        "TreinoId": treino_id,
                        "TreinoNome": treino_nome,
                        "TreinoObs": treino_obs,
                        "Status": status,
                        "FrequenciaSemanal": freq_semanal,
                        "QtdeTreinosRealizados": qtde_utilizado,
                        "DataCriacao": data_criacao,
                        "DataAlteracao": data_alteracao,
                        "Sessao": idx_sessao,
                        "OrdemExercicio": ex.get("Ordem"),
                        "Exercicio": ex_info.get("Nome") or "",
                        "GrupoMuscular": grupo_nome,
                        "Series": ex.get("QtdeSeries"),
                        "Repeticoes": ex.get("Repeticoes") or "",
                        "Carga": ex.get("Carga") or "",
                        "Intervalo": ex.get("Intervalo") or "",
                        "Observacoes": ex.get("Observacoes") or "",
                    })

        return rows

    def treinos_completos(
        self, clientes_ativos: set[int] | None = None,
    ) -> list[dict[str, Any]]:
        """Retorna todos os treinos com detalhes achatados para planilha.

        Cada linha = 1 exercício de 1 sessão de 1 treino.
        Se `clientes_ativos` for fornecido, retorna apenas de clientes ativos.
        """
        grupos_map = self.grupos_exercicio()
        resumos = self.listar_treinos(clientes_ativos=clientes_ativos)
        data_captura = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
        return self._build_treino_rows(resumos, grupos_map, data_captura)

    def historico_treinos(
        self,
        datas_existentes: set[str] | None = None,
        clientes_ativos: set[int] | None = None,
    ) -> list[dict[str, Any]]:
        """Retorna dados de treino para o histórico (acumulativo).

        Se `datas_existentes` for fornecido e a data de hoje já estiver nele,
        pula para evitar duplicatas.
        Se `clientes_ativos` for fornecido, retorna apenas de clientes ativos.
        """
        data_hoje = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")

        if datas_existentes and data_hoje in datas_existentes:
            return []

        grupos_map = self.grupos_exercicio()
        resumos = self.listar_treinos(clientes_ativos=clientes_ativos)
        return self._build_treino_rows(resumos, grupos_map, data_hoje)
