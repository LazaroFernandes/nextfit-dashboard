"""Entrypoint: puxa todos os recursos da API NextFit e escreve em Google Sheets.

Uso:
    python src/sync.py              # sincroniza tudo
    python src/sync.py clientes     # sincroniza só alguns (nomes abaixo)
"""
from __future__ import annotations

import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv

from nextfit_client import NextFitClient
from nextfit_v2_client import NextFitV2Client, TokenExpiredError
from sheets_client import SheetsClient

# Ordem intencional: dados "mestre" antes de dados que fazem referência a eles
RESOURCES: dict[str, str] = {
    "clientes": "Clientes",
    "leads": "Leads",
    "usuarios": "Usuarios",
    "contratos_base": "ContratosBase",
    "contratos_cliente": "ContratosCliente",
    "vendas": "Vendas",
    "contas_receber": "ContasReceber",
    "movimentos_financeiros": "MovimentosFinanceiros",
    "oportunidades": "Oportunidades",
    "agenda": "Agenda",
}

# Recursos extras que usam a API v2 interna (requer NEXTFIT_V2_TOKEN)
V2_RESOURCES: dict[str, str] = {
    "presencas": "Presencas",
    "treinos": "Treinos",
    "execucoes": "HistoricoExecucoes",
}

# Aba auxiliar usada pelo fluxo de detecção de execução (snapshot por treino)
FICHAS_STATUS_TAB = "FichasStatus"


def _parse_iso(s: str) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None


def _resolve_presencas_window() -> tuple[datetime, datetime, str]:
    """Retorna (data_inicial, data_final, rotulo) em UTC.

    Se NEXTFIT_PRESENCAS_DATA_INICIAL estiver definida (formato YYYY-MM-DD),
    usa ela como inicio; caso contrario usa NEXTFIT_PRESENCAS_DIAS (default 30).
    """
    data_final = datetime.now(tz=timezone.utc)
    raw_inicio = os.getenv("NEXTFIT_PRESENCAS_DATA_INICIAL", "").strip()
    if raw_inicio:
        try:
            data_inicial = datetime.strptime(raw_inicio, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            print(
                f"[aviso] NEXTFIT_PRESENCAS_DATA_INICIAL invalida ('{raw_inicio}'); "
                "esperado YYYY-MM-DD. Usando NEXTFIT_PRESENCAS_DIAS.",
                file=sys.stderr,
            )
            raw_inicio = ""
    if not raw_inicio:
        dias = int(os.getenv("NEXTFIT_PRESENCAS_DIAS", "30").strip() or "30")
        data_inicial = data_final - timedelta(days=dias)
        rotulo = f"ultimos {dias} dias"
    else:
        rotulo = f"desde {data_inicial.date().isoformat()}"
    return data_inicial, data_final, rotulo


def _build_frequencia_resumo(
    presencas: list[dict],
    professor_por_cliente: dict[int, str] | None = None,
) -> list[dict]:
    """Agrega presencas por cliente -> resumo tipo tabela dinamica."""
    professor_por_cliente = professor_por_cliente or {}
    agg: dict[int, dict] = {}
    for p in presencas:
        codigo = p.get("CodigoCliente")
        if codigo is None:
            continue
        data = _parse_iso(p.get("Data") or "")
        tipo = (p.get("DescricaoTipo") or "").strip()
        entry = agg.setdefault(codigo, {
            "CodigoCliente": codigo,
            "NomeCliente": p.get("NomeCliente") or "",
            "DddCliente": p.get("DddCliente") or "",
            "FoneCliente": p.get("FoneCliente") or "",
            "DescricaoContrato": p.get("DescricaoContrato") or "",
            "DescricaoModalidade": p.get("DescricaoModalidade") or "",
            "TotalAcessos": 0,
            "TotalAgendas": 0,
            "Total": 0,
            "PrimeiroAcesso": None,
            "UltimoAcesso": None,
        })
        if tipo == "Acesso":
            entry["TotalAcessos"] += 1
        elif tipo == "Agenda":
            entry["TotalAgendas"] += 1
        entry["Total"] += 1
        if data is not None:
            if entry["PrimeiroAcesso"] is None or data < entry["PrimeiroAcesso"]:
                entry["PrimeiroAcesso"] = data
            if entry["UltimoAcesso"] is None or data > entry["UltimoAcesso"]:
                entry["UltimoAcesso"] = data

    agora = datetime.now(tz=timezone.utc)
    resumo: list[dict] = []
    for e in agg.values():
        primeiro = e["PrimeiroAcesso"]
        ultimo = e["UltimoAcesso"]
        dias_sem_vir = (agora - ultimo).days if ultimo else None
        resumo.append({
            "NomeCliente": e["NomeCliente"],
            "CodigoCliente": e["CodigoCliente"],
            "Professor": professor_por_cliente.get(e["CodigoCliente"], ""),
            "Telefone": f"({e['DddCliente']}) {e['FoneCliente']}".strip(),
            "Contrato": e["DescricaoContrato"],
            "Modalidade": e["DescricaoModalidade"],
            "Total": e["Total"],
            "Acessos": e["TotalAcessos"],
            "Agendas": e["TotalAgendas"],
            "PrimeiroAcesso": primeiro.strftime("%Y-%m-%d %H:%M") if primeiro else "",
            "UltimoAcesso": ultimo.strftime("%Y-%m-%d %H:%M") if ultimo else "",
            "DiasSemVir": dias_sem_vir if dias_sem_vir is not None else "",
        })
    # Ordena por total de presencas desc (alunos mais frequentes no topo)
    resumo.sort(key=lambda r: (-r["Total"], r["NomeCliente"]))
    return resumo


def _env(name: str, required: bool = True) -> str:
    val = os.getenv(name, "").strip()
    if required and not val:
        print(f"[erro] variavel {name} nao esta definida no .env", file=sys.stderr)
        sys.exit(1)
    return val


def main() -> int:
    # Carrega .env da raiz do projeto
    project_root = Path(__file__).resolve().parent.parent
    load_dotenv(project_root / ".env")

    api_key = _env("NEXTFIT_API_KEY")
    base_url = _env("NEXTFIT_BASE_URL")
    version = os.getenv("NEXTFIT_API_VERSION", "1").strip() or "1"
    sheet_id = _env("GOOGLE_SHEET_ID")
    creds_file = _env("GOOGLE_CREDENTIALS_FILE")

    # Resolve o caminho do arquivo de credenciais relativo à raiz do projeto
    creds_path = Path(creds_file)
    if not creds_path.is_absolute():
        creds_path = project_root / creds_path
    if not creds_path.exists():
        print(f"[erro] arquivo de credenciais nao encontrado: {creds_path}", file=sys.stderr)
        return 1

    # Todos os recursos possíveis (público + v2)
    all_resources = {**RESOURCES, **V2_RESOURCES}

    # Filtro opcional de recursos via CLI
    args = [a.lower() for a in sys.argv[1:]]
    if args:
        unknown = [a for a in args if a not in all_resources]
        if unknown:
            print(f"[erro] recursos desconhecidos: {unknown}", file=sys.stderr)
            print(f"validos: {list(all_resources.keys())}", file=sys.stderr)
            return 1
        selected_public = {k: RESOURCES[k] for k in args if k in RESOURCES}
        selected_v2 = {k: V2_RESOURCES[k] for k in args if k in V2_RESOURCES}
    else:
        selected_public = RESOURCES
        selected_v2 = V2_RESOURCES

    print(f"[info] conectando no NextFit em {base_url}")
    nf = NextFitClient(api_key=api_key, base_url=base_url, version=version)

    print(f"[info] abrindo planilha {sheet_id}")
    sheets = SheetsClient(credentials_file=str(creds_path), sheet_id=sheet_id)

    total_start = time.time()

    # --- API publica ---
    for method_name, tab_name in selected_public.items():
        print(f"[sync] {method_name} -> aba '{tab_name}' ...", flush=True)
        t0 = time.time()
        try:
            items = getattr(nf, method_name)()
        except Exception as e:
            print(f"  [falha] erro ao buscar {method_name}: {e}", file=sys.stderr)
            continue
        fetched = len(items)
        try:
            written = sheets.write_tab(tab_name, items)
        except Exception as e:
            print(f"  [falha] erro ao escrever '{tab_name}': {e}", file=sys.stderr)
            continue
        elapsed = time.time() - t0
        print(f"  [ok] {fetched} registros lidos, {written} escritos ({elapsed:.1f}s)")

    # --- API v2 interna (presencas + treinos) ---
    if selected_v2:
        v2_token = os.getenv("NEXTFIT_V2_TOKEN", "").strip()
        codigo_unidade = os.getenv("NEXTFIT_CODIGO_UNIDADE", "").strip()
        refresh_token = os.getenv("NEXTFIT_V2_REFRESH_TOKEN", "").strip() or None
        if not v2_token or not codigo_unidade:
            print(
                "[aviso] NEXTFIT_V2_TOKEN ou NEXTFIT_CODIGO_UNIDADE nao configurados; "
                f"pulando recursos v2: {list(selected_v2.keys())}",
                file=sys.stderr,
            )
        else:
            env_file = project_root / ".env"
            nf_v2 = NextFitV2Client(
                token=v2_token,
                codigo_unidade=codigo_unidade,
                refresh_token=refresh_token,
                env_path=env_file,
            )

            # --- Presencas ---
            if "presencas" in selected_v2:
                data_inicial, data_final, rotulo = _resolve_presencas_window()
                tab_name = selected_v2["presencas"]
                print(f"[sync] presencas ({rotulo}) -> aba '{tab_name}' ...", flush=True)
                t0 = time.time()
                try:
                    items = nf_v2.presencas(data_inicial, data_final)
                except TokenExpiredError as e:
                    print(f"  [falha] {e}", file=sys.stderr)
                    items = []
                except Exception as e:
                    print(f"  [falha] erro ao buscar presencas: {e}", file=sys.stderr)
                    items = []

                if items:
                    fetched = len(items)
                    try:
                        written = sheets.write_tab(tab_name, items)
                    except Exception as e:
                        print(f"  [falha] erro ao escrever '{tab_name}': {e}", file=sys.stderr)
                    else:
                        elapsed = time.time() - t0
                        print(f"  [ok] {fetched} registros lidos, {written} escritos ({elapsed:.1f}s)")

                    # Gera aba FrequenciaResumo
                    t0 = time.time()
                    print("  [resumo] buscando clientes e usuarios para cruzar professor...", flush=True)
                    try:
                        clientes_list = nf.clientes()
                        usuarios_list = nf.usuarios()
                    except Exception as e:
                        print(f"  [aviso] nao foi possivel buscar clientes/usuarios: {e}", file=sys.stderr)
                        clientes_list, usuarios_list = [], []

                    nome_por_usuario = {u.get("id"): (u.get("nome") or "") for u in usuarios_list}
                    professor_por_cliente: dict[int, str] = {}
                    for c in clientes_list:
                        codigo = c.get("id")
                        cliente_sub = c.get("cliente") or {}
                        codigo_prof = cliente_sub.get("codigoUsuarioProfessor")
                        if codigo is not None and codigo_prof is not None:
                            professor_por_cliente[codigo] = nome_por_usuario.get(codigo_prof, "")

                    resumo = _build_frequencia_resumo(items, professor_por_cliente)
                    try:
                        written = sheets.write_tab("FrequenciaResumo", resumo)
                    except Exception as e:
                        print(f"  [falha] erro ao escrever 'FrequenciaResumo': {e}", file=sys.stderr)
                    else:
                        elapsed = time.time() - t0
                        com_prof = sum(1 for r in resumo if r["Professor"])
                        print(
                            f"  [ok] {len(resumo)} alunos no resumo, "
                            f"{com_prof} com professor ({elapsed:.1f}s)"
                        )

            # --- Buscar clientes com plano ativo (para filtrar treinos) ---
            clientes_ativos: set[int] | None = None
            if "treinos" in selected_v2 or "execucoes" in selected_v2:
                print("[info] buscando clientes com plano ativo...", flush=True)
                try:
                    contratos = nf.contratos_cliente()
                    clientes_ativos = {
                        c.get("codigoCliente")
                        for c in contratos
                        if c.get("status") == "Ativo" and c.get("codigoCliente") is not None
                    }
                    print(f"  [ok] {len(clientes_ativos)} clientes com plano ativo")
                except Exception as e:
                    print(f"  [aviso] nao foi possivel filtrar por plano ativo: {e}", file=sys.stderr)

            # --- Treinos ---
            if "treinos" in selected_v2:
                tab_name = selected_v2["treinos"]
                print(f"[sync] treinos (somente planos ativos) -> aba '{tab_name}' ...", flush=True)
                t0 = time.time()
                try:
                    items = nf_v2.treinos_completos(clientes_ativos=clientes_ativos)
                except TokenExpiredError as e:
                    print(f"  [falha] {e}", file=sys.stderr)
                    items = []
                except Exception as e:
                    print(f"  [falha] erro ao buscar treinos: {e}", file=sys.stderr)
                    items = []

                if items:
                    fetched = len(items)
                    try:
                        written = sheets.write_tab(tab_name, items)
                    except Exception as e:
                        print(f"  [falha] erro ao escrever '{tab_name}': {e}", file=sys.stderr)
                    else:
                        elapsed = time.time() - t0
                        print(f"  [ok] {fetched} exercicios de treino lidos, {written} escritos ({elapsed:.1f}s)")

            # --- Detecção de execuções (incremental, baseado em QtdeUtilizado) ---
            if "execucoes" in selected_v2:
                tab_name = selected_v2["execucoes"]
                print(
                    f"[sync] execucoes (delta de QtdeUtilizado) -> aba '{tab_name}' ...",
                    flush=True,
                )
                t0 = time.time()

                # Lê snapshot anterior dos treinos
                try:
                    status_rows = sheets.read_tab_all(FICHAS_STATUS_TAB)
                except Exception as e:
                    print(f"  [aviso] nao foi possivel ler '{FICHAS_STATUS_TAB}': {e}", file=sys.stderr)
                    status_rows = []

                status_anterior: dict[int, dict] = {}
                for r in status_rows:
                    try:
                        status_anterior[int(r["TreinoId"])] = r
                    except (KeyError, TypeError, ValueError):
                        continue

                if not status_anterior:
                    print(
                        "  [info] FichasStatus vazia — inicializando snapshot "
                        "(nenhuma execução será registrada nesta rodada)"
                    )

                try:
                    linhas_novas, novo_status = nf_v2.detectar_execucoes(
                        status_anterior=status_anterior,
                        clientes_ativos=clientes_ativos,
                    )
                except TokenExpiredError as e:
                    print(f"  [falha] {e}", file=sys.stderr)
                    linhas_novas, novo_status = [], []
                except Exception as e:
                    print(f"  [falha] erro ao detectar execucoes: {e}", file=sys.stderr)
                    linhas_novas, novo_status = [], []

                # Grava linhas novas em HistoricoExecucoes (append)
                if linhas_novas:
                    try:
                        written = sheets.append_tab(tab_name, linhas_novas)
                    except Exception as e:
                        print(f"  [falha] erro ao escrever '{tab_name}': {e}", file=sys.stderr)
                    else:
                        elapsed = time.time() - t0
                        print(
                            f"  [ok] {len(linhas_novas)} linhas de execucao detectadas, "
                            f"{written} adicionadas ({elapsed:.1f}s)"
                        )
                else:
                    elapsed = time.time() - t0
                    print(f"  [ok] nenhuma execucao nova detectada ({elapsed:.1f}s)")

                # Atualiza FichasStatus (overwrite)
                if novo_status:
                    try:
                        sheets.write_tab(FICHAS_STATUS_TAB, novo_status)
                        print(f"  [ok] '{FICHAS_STATUS_TAB}' atualizado ({len(novo_status)} fichas)")
                    except Exception as e:
                        print(f"  [falha] erro ao escrever '{FICHAS_STATUS_TAB}': {e}", file=sys.stderr)

    print(f"[fim] sincronizacao concluida em {time.time() - total_start:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
