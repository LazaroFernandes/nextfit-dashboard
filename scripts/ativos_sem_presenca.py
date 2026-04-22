"""Alunos com contrato ATIVO que nao tiveram NENHUMA presenca no periodo de analise.

Gera enriquecimento completo e grava na aba 'AtivosSemPresenca' da planilha:
  - Dados pessoais (telefone, email)
  - Contrato ativo (descricao, valor, data inicio)
  - Historico de acessos (ultimo acesso ate 180 dias atras)
  - Categoria de risco (Nunca acessou, Novo sem engajamento, Sumiu recente/antigo)

Janelas configuraveis no .env:
  - NEXTFIT_PRESENCAS_DATA_INICIAL / NEXTFIT_PRESENCAS_DIAS : periodo de analise
  - NEXTFIT_HISTORICO_DIAS : janela historica pra "ultimo acesso" (default 180)
"""
from __future__ import annotations

import os
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from dotenv import load_dotenv

from nextfit_client import NextFitClient
from nextfit_v2_client import NextFitV2Client
from sheets_client import SheetsClient

ENV_PATH = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(ENV_PATH)


def _resolve_analise_window() -> tuple[datetime, datetime, str]:
    data_final = datetime.now(tz=timezone.utc)
    raw = os.getenv("NEXTFIT_PRESENCAS_DATA_INICIAL", "").strip()
    if raw:
        try:
            data_inicial = datetime.strptime(raw, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            return data_inicial, data_final, f"desde {raw}"
        except ValueError:
            pass
    dias = int(os.getenv("NEXTFIT_PRESENCAS_DIAS", "30").strip() or "30")
    return data_final - timedelta(days=dias), data_final, f"ultimos {dias} dias"


def _parse_iso(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None
    # Normaliza pra tz-aware (UTC) — a API às vezes devolve naive
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _fmt_date(dt: datetime | None) -> str:
    return dt.strftime("%Y-%m-%d") if dt else ""


def _fmt_money(v: float | int | None) -> str:
    if v is None:
        return ""
    try:
        return f"R$ {float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (TypeError, ValueError):
        return ""


def _categorizar(
    dias_desde_cadastro: int | None,
    dias_sem_vir_hist: int | None,
    dias_analise_window: int,
) -> str:
    """Categoria de risco.

    - 'Nunca acessou (cliente novo)'  : cadastrado <30d, sem presenca
    - 'Novo sem engajamento'          : cadastrado 30-90d, sem presenca no historico
    - 'Sumiu recente'                 : ultima presenca 1-30d antes do inicio do periodo
    - 'Sumiu ha tempo'                : ultima presenca 30-90d antes do inicio
    - 'Sumiu ha muito'                : ultima presenca >90d antes ou sem registro no historico
    """
    if dias_sem_vir_hist is None:
        # Sem nenhuma presenca no historico
        if dias_desde_cadastro is not None and dias_desde_cadastro < 30:
            return "Nunca acessou (cliente novo)"
        if dias_desde_cadastro is not None and dias_desde_cadastro < 90:
            return "Novo sem engajamento"
        return "Sumiu ha muito (sem registro no historico)"

    # tem ultima presenca; quantos dias antes do inicio do periodo?
    dias_antes_periodo = dias_sem_vir_hist - dias_analise_window
    if dias_antes_periodo <= 30:
        return "Sumiu recente"
    if dias_antes_periodo <= 90:
        return "Sumiu ha tempo"
    return "Sumiu ha muito"


def main() -> None:
    nf = NextFitClient(
        api_key=os.environ["NEXTFIT_API_KEY"],
        base_url=os.environ["NEXTFIT_BASE_URL"],
        version=os.environ.get("NEXTFIT_API_VERSION", "1"),
    )
    v2 = NextFitV2Client(
        token=os.environ["NEXTFIT_V2_TOKEN"],
        codigo_unidade=int(os.environ["NEXTFIT_CODIGO_UNIDADE"]),
        refresh_token=os.environ.get("NEXTFIT_V2_REFRESH_TOKEN"),
        env_path=ENV_PATH,
    )
    sheets = SheetsClient(
        credentials_file=os.environ["GOOGLE_CREDENTIALS_FILE"],
        sheet_id=os.environ["GOOGLE_SHEET_ID"],
    )

    # Janelas
    data_inicial, data_final, rotulo_analise = _resolve_analise_window()
    dias_analise = max(1, (data_final - data_inicial).days)
    historico_dias = int(os.getenv("NEXTFIT_HISTORICO_DIAS", "180").strip() or "180")
    data_inicial_hist = data_final - timedelta(days=historico_dias)

    print(f"[info] periodo de analise: {rotulo_analise} ({dias_analise} dias)")
    print(f"[info] janela historica: {historico_dias} dias (para calcular 'ultimo acesso')")

    print("[1/4] Buscando clientes, contratos, usuarios...")
    clientes = nf.clientes()
    contratos = nf.contratos_cliente()
    usuarios = nf.usuarios()
    print(f"  {len(clientes)} clientes, {len(contratos)} contratos, {len(usuarios)} usuarios")

    # Indices
    cliente_por_codigo = {c["id"]: c for c in clientes}
    nome_usuario = {u["id"]: u.get("nome") or "" for u in usuarios}

    # Professor por cliente
    professor_por_cliente: dict[int, str] = {}
    for c in clientes:
        sub = c.get("cliente") or {}
        prof = sub.get("codigoUsuarioProfessor")
        if prof is not None:
            professor_por_cliente[c["id"]] = nome_usuario.get(prof, f"(usuario {prof})")

    # Contratos ativos por cliente: pega o mais recente (dataInicio) com status Ativo
    contratos_ativos_por_cliente: dict[int, dict] = {}
    for ct in contratos:
        if ct.get("status") != "Ativo":
            continue
        cod = ct.get("codigoCliente")
        if cod is None:
            continue
        atual = contratos_ativos_por_cliente.get(cod)
        if atual is None:
            contratos_ativos_por_cliente[cod] = ct
        else:
            d_novo = _parse_iso(ct.get("dataInicio"))
            d_atual = _parse_iso(atual.get("dataInicio"))
            if d_novo and (not d_atual or d_novo > d_atual):
                contratos_ativos_por_cliente[cod] = ct

    com_contrato_ativo = set(contratos_ativos_por_cliente.keys())

    # Descricao do contrato base (id -> descricao)
    contratos_base = nf.contratos_base()
    desc_contrato_base = {cb["id"]: cb.get("descricao") or "" for cb in contratos_base}

    print(f"[2/4] Buscando presencas janela historica ({historico_dias}d)...")
    presencas_hist = v2.presencas(data_inicial_hist, data_final)
    print(f"  {len(presencas_hist)} registros de presenca no historico")

    # Agrega: por cliente -> (ultima_data, total_no_historico, presencas_no_periodo_analise)
    ultima_por_cliente: dict[int, datetime] = {}
    total_hist_por_cliente: Counter[int] = Counter()
    presencas_no_periodo_por_cliente: Counter[int] = Counter()
    for p in presencas_hist:
        cod = p.get("CodigoCliente")
        dt = _parse_iso(p.get("Data"))
        if cod is None or dt is None:
            continue
        total_hist_por_cliente[cod] += 1
        if dt >= data_inicial:
            presencas_no_periodo_por_cliente[cod] += 1
        if cod not in ultima_por_cliente or dt > ultima_por_cliente[cod]:
            ultima_por_cliente[cod] = dt

    codigos_com_presenca_no_periodo = set(presencas_no_periodo_por_cliente.keys())

    # Filtro principal: ativos sem presenca no periodo
    ativos = {c for c in com_contrato_ativo if not cliente_por_codigo.get(c, {}).get("inativo")}
    sem_presenca = ativos - codigos_com_presenca_no_periodo

    print(f"[3/4] Montando {len(sem_presenca)} linhas...")
    agora = datetime.now(tz=timezone.utc)
    linhas: list[dict] = []
    for cod in sem_presenca:
        cli = cliente_por_codigo.get(cod, {})
        ct = contratos_ativos_por_cliente.get(cod, {})
        data_cadastro = _parse_iso(cli.get("dataCadastro"))
        dias_desde_cadastro = (agora - data_cadastro).days if data_cadastro else None

        ultima = ultima_por_cliente.get(cod)
        dias_sem_vir = (agora - ultima).days if ultima else None

        categoria = _categorizar(dias_desde_cadastro, dias_sem_vir, dias_analise)

        tel_ddd = cli.get("dddFone") or ""
        tel_num = cli.get("fone") or ""
        telefone = f"({tel_ddd}) {tel_num}".strip() if tel_ddd or tel_num else ""

        cod_base = ct.get("codigoContratoBase")
        contrato_desc = desc_contrato_base.get(cod_base, "") if cod_base else ""

        linhas.append({
            "Categoria": categoria,
            "NomeCliente": cli.get("nome") or "",
            "CodigoCliente": cod,
            "Professor": professor_por_cliente.get(cod, ""),
            "Telefone": telefone,
            "Email": cli.get("email") or "",
            "DataCadastro": _fmt_date(data_cadastro),
            "DiasDesdeCadastro": dias_desde_cadastro if dias_desde_cadastro is not None else "",
            "Contrato": contrato_desc,
            "ValorContrato": _fmt_money(ct.get("valorTotal")),
            "DataInicioContrato": _fmt_date(_parse_iso(ct.get("dataInicio"))),
            "UltimoAcesso": _fmt_date(ultima),
            "DiasSemVir": dias_sem_vir if dias_sem_vir is not None else "",
            "TotalAcessosHistorico": total_hist_por_cliente.get(cod, 0),
        })

    # Ordem: por categoria (severidade) depois por nome
    ordem_cat = {
        "Sumiu ha muito (sem registro no historico)": 1,
        "Sumiu ha muito": 2,
        "Sumiu ha tempo": 3,
        "Sumiu recente": 4,
        "Novo sem engajamento": 5,
        "Nunca acessou (cliente novo)": 6,
    }
    linhas.sort(key=lambda r: (ordem_cat.get(r["Categoria"], 99), r["NomeCliente"].lower()))

    # Grava no Sheets
    print("[4/4] Gravando aba 'AtivosSemPresenca'...")
    sheets.write_tab("AtivosSemPresenca", linhas)

    # Sumario console
    print()
    print("=" * 70)
    print("SUMARIO")
    print("=" * 70)
    print(f"Clientes cadastrados:          {len(clientes)}")
    print(f"Marcados 'Inativo':            {sum(1 for c in clientes if c.get('inativo'))}")
    print(f"Com contrato 'Ativo':          {len(com_contrato_ativo)}")
    print(f"Ativos (nao inativo + contrato): {len(ativos)}")
    print(f"Com presenca no periodo:       {len(ativos & codigos_com_presenca_no_periodo)}")
    print(f"SEM PRESENCA no periodo:       {len(sem_presenca)}")
    print()
    print("Por categoria de risco:")
    cnt_cat = Counter(r["Categoria"] for r in linhas)
    for cat in sorted(cnt_cat.keys(), key=lambda k: ordem_cat.get(k, 99)):
        print(f"  {cnt_cat[cat]:>3}  {cat}")
    print()
    print("Por professor (top 10):")
    cnt_prof = Counter(r["Professor"] or "(sem professor)" for r in linhas)
    for prof, n in cnt_prof.most_common(10):
        print(f"  {n:>3}  {prof}")

    # Valor em risco (soma dos contratos)
    valor_em_risco = 0.0
    for cod in sem_presenca:
        v = contratos_ativos_por_cliente.get(cod, {}).get("valorTotal")
        if isinstance(v, (int, float)):
            valor_em_risco += float(v)
    print()
    print(f"Valor total dos contratos em risco: {_fmt_money(valor_em_risco)}")


if __name__ == "__main__":
    main()
