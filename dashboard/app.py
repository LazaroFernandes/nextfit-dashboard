"""Dashboard Streamlit — evolução de cargas por aluno.

Lê a aba HistoricoTreinos do Google Sheets. Cada DataCaptura é um snapshot
do treino do aluno naquele dia; a evolução é a série temporal de Carga
para um mesmo par (Exercicio, Sessao).

Para rodar:
    streamlit run dashboard/app.py
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))
load_dotenv(PROJECT_ROOT / ".env")

from sheets_client import SheetsClient  # noqa: E402


def _build_sheets_client() -> SheetsClient:
    """Cria SheetsClient priorizando st.secrets (prod) e caindo pra .env (dev local)."""
    service_account_info: dict | None = None
    sheet_id: str | None = None
    try:
        if "gcp_service_account" in st.secrets:
            service_account_info = dict(st.secrets["gcp_service_account"])
        if "GOOGLE_SHEET_ID" in st.secrets:
            sheet_id = st.secrets["GOOGLE_SHEET_ID"]
    except Exception:
        pass  # secrets.toml ausente — usa .env

    sheet_id = sheet_id or os.environ["GOOGLE_SHEET_ID"]

    if service_account_info is not None:
        return SheetsClient(credentials_info=service_account_info, sheet_id=sheet_id)

    return SheetsClient(
        credentials_file=str(PROJECT_ROOT / os.environ["GOOGLE_CREDENTIALS_FILE"]),
        sheet_id=sheet_id,
    )

SERIES_POR_EXERCICIO = 3

st.set_page_config(
    page_title="Evolução dos alunos",
    layout="wide",
    page_icon="💪",
)


@st.cache_data(ttl=300, show_spinner="Carregando histórico...")
def carregar_historico() -> pd.DataFrame:
    client = _build_sheets_client()
    ws = client.spreadsheet.worksheet("HistoricoTreinos")
    rows = ws.get_all_records()
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df["DataCaptura"] = pd.to_datetime(df["DataCaptura"], errors="coerce")
    df["CargaNum"] = df["Carga"].astype(str).apply(_parse_carga)
    return df


def _parse_carga(valor: str) -> float | None:
    """Extrai a carga máxima da string (formato multi-série tipo '20/20/22/0').

    Zeros são ignorados (representam séries não utilizadas no cadastro).
    """
    if not valor or valor.lower() in {"nan", "none", ""}:
        return None
    numeros = [
        float(m.replace(",", "."))
        for m in re.findall(r"\d+(?:[.,]\d+)?", valor)
    ]
    positivos = [n for n in numeros if n > 0]
    if not positivos:
        return None
    return max(positivos)


@st.dialog("📈 Evolução do exercício", width="large")
def mostrar_evolucao(df_ex: pd.DataFrame, exercicio: str, sessao: str) -> None:
    st.markdown(f"### {exercicio}")
    st.caption(f"Sessão {sessao} · {len(df_ex)} registro(s)")

    dados = df_ex.sort_values("DataCaptura").copy()
    plotaveis = dados.dropna(subset=["DataCaptura", "CargaNum"])

    if plotaveis.empty:
        st.info("Ainda não há cargas numéricas para plotar. Mostrando histórico textual.")
    else:
        chart = plotaveis.set_index("DataCaptura")[["CargaNum"]].rename(
            columns={"CargaNum": "Carga máx. (kg)"}
        )
        st.line_chart(chart, height=360)
        st.caption("Carga máxima por sessão (ignora séries com carga 0).")

        c1, c2, c3 = st.columns(3)
        c1.metric("Última", f"{plotaveis['CargaNum'].iloc[-1]:g} kg")
        c2.metric("Recorde", f"{plotaveis['CargaNum'].max():g} kg")
        delta = plotaveis["CargaNum"].iloc[-1] - plotaveis["CargaNum"].iloc[0]
        c3.metric(
            "Variação total",
            f"{delta:+g} kg",
            delta=f"{delta:+g}" if delta else None,
        )

    st.markdown("#### Histórico completo")
    cols_hist = [
        c for c in ["DataCaptura", "Carga", "Repeticoes", "Series", "Intervalo", "Observacoes"]
        if c in dados.columns
    ]
    st.dataframe(
        dados[cols_hist].rename(columns={"DataCaptura": "Data"}),
        hide_index=True,
        use_container_width=True,
    )


def main() -> None:
    st.title("💪 Evolução dos alunos")

    df = carregar_historico()
    if df.empty:
        st.warning("Nenhum dado encontrado na aba HistoricoTreinos.")
        return

    alunos = (
        df[["CodigoCliente", "NomeCliente"]]
        .dropna()
        .drop_duplicates()
        .sort_values("NomeCliente")
    )
    nome_map = {
        f"{row.NomeCliente}": row.CodigoCliente
        for row in alunos.itertuples()
    }
    nome_sel = st.sidebar.selectbox("Aluno", list(nome_map.keys()))
    cod_sel = nome_map[nome_sel]

    df_aluno = df[df["CodigoCliente"] == cod_sel]
    if df_aluno.empty:
        st.info("Aluno sem histórico.")
        return

    ultima_data = df_aluno["DataCaptura"].max()
    treino_atual = df_aluno[df_aluno["DataCaptura"] == ultima_data]

    datas = sorted(df_aluno["DataCaptura"].dropna().unique())
    st.caption(
        f"Última captura: **{pd.Timestamp(ultima_data).date()}** · "
        f"{len(datas)} captura(s) no histórico"
    )

    col_treino, col_volume = st.columns([2, 1])

    with col_treino:
        st.subheader("Treino atual")
        sessoes = sorted(treino_atual["Sessao"].dropna().unique())
        if not sessoes:
            st.info("Sem sessões registradas na captura mais recente.")
        for sessao in sessoes:
            bloco = treino_atual[treino_atual["Sessao"] == sessao]
            st.markdown(f"#### Sessão {sessao}")
            for idx, ex in bloco.iterrows():
                with st.container(border=True):
                    c1, c2 = st.columns([4, 1])
                    with c1:
                        st.markdown(f"**{ex['Exercicio']}**")
                        partes = []
                        if ex.get("GrupoMuscular"):
                            partes.append(f"🎯 {ex['GrupoMuscular']}")
                        if ex.get("Carga"):
                            partes.append(f"⚖️ {ex['Carga']}")
                        if ex.get("Repeticoes"):
                            partes.append(f"🔁 {ex['Repeticoes']}")
                        if ex.get("Intervalo"):
                            partes.append(f"⏱️ {ex['Intervalo']}")
                        if partes:
                            st.caption(" · ".join(str(p) for p in partes))
                    with c2:
                        key = f"evo_{sessao}_{idx}"
                        if st.button("📈 Evolução", key=key, use_container_width=True):
                            df_ex = df_aluno[
                                (df_aluno["Exercicio"] == ex["Exercicio"])
                                & (df_aluno["Sessao"] == sessao)
                            ]
                            mostrar_evolucao(df_ex, ex["Exercicio"], sessao)

    with col_volume:
        st.subheader("Volume por grupo muscular")
        st.caption(f"Séries totais ({SERIES_POR_EXERCICIO} por exercício)")
        volume = (
            treino_atual[treino_atual["GrupoMuscular"].astype(bool)]
            .groupby("GrupoMuscular")
            .size()
            .reset_index(name="Exercícios")
        )
        if volume.empty:
            st.info("Sem grupos musculares mapeados.")
        else:
            volume["Séries"] = volume["Exercícios"] * SERIES_POR_EXERCICIO
            volume = volume.sort_values("Séries", ascending=False)
            volume = volume.rename(columns={"GrupoMuscular": "Grupo"})
            total_series = int(volume["Séries"].sum())
            st.metric("Volume total", f"{total_series} séries")
            st.dataframe(volume, hide_index=True, use_container_width=True)

    with st.expander("🔄 Atualizar dados"):
        if st.button("Recarregar do Google Sheets"):
            carregar_historico.clear()
            st.rerun()


if __name__ == "__main__":
    main()
