"""Dashboard Streamlit — evolução de cargas por aluno.

Lê duas abas do Google Sheets:
- `Treinos`: estado atual da ficha de cada aluno (overwrite a cada sync)
- `HistoricoExecucoes`: log de execuções (1 entrada por sessão concluída)

A evolução é a série temporal de Carga em HistoricoExecucoes para um mesmo
par (Exercicio, Sessao). O "Treino atual" e o "Volume" vêm de Treinos.

Para rodar:
    streamlit run dashboard/app.py
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import altair as alt
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


def _carregar_aba(tab_name: str) -> pd.DataFrame:
    client = _build_sheets_client()
    try:
        ws = client.spreadsheet.worksheet(tab_name)
    except Exception:
        return pd.DataFrame()
    rows = ws.get_all_records()
    return pd.DataFrame(rows)


@st.cache_data(ttl=300, show_spinner="Carregando execuções...")
def carregar_execucoes() -> pd.DataFrame:
    df = _carregar_aba("HistoricoExecucoes")
    if df.empty:
        return df
    # Prioriza TimestampExecucao (momento exato); cai pra DataCaptura (YYYY-MM-DD)
    if "TimestampExecucao" in df.columns:
        df["DataExecucao"] = pd.to_datetime(df["TimestampExecucao"], errors="coerce", utc=True)
    else:
        df["DataExecucao"] = pd.NaT
    fallback = pd.to_datetime(df.get("DataCaptura"), errors="coerce")
    df["DataExecucao"] = df["DataExecucao"].fillna(fallback)
    df["CargaNum"] = df["Carga"].astype(str).apply(_parse_carga)
    return df


@st.cache_data(ttl=300, show_spinner="Carregando treinos...")
def carregar_treinos() -> pd.DataFrame:
    df = _carregar_aba("Treinos")
    if df.empty:
        return df
    df["DataCaptura"] = pd.to_datetime(df.get("DataCaptura"), errors="coerce")
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
    st.caption(f"Sessão {sessao} · {len(df_ex)} execução(ões)")

    if df_ex.empty or "DataExecucao" not in df_ex.columns:
        st.info("Ainda não há execuções registradas pra este exercício.")
        return

    dados = df_ex.sort_values("DataExecucao").copy()
    plotaveis = dados.dropna(subset=["DataExecucao", "CargaNum"])

    if plotaveis.empty:
        st.info("Ainda não há cargas numéricas para plotar. Mostrando histórico textual.")
    else:
        chart_df = plotaveis[["DataExecucao", "CargaNum"]].rename(
            columns={"DataExecucao": "Data", "CargaNum": "Carga"}
        )
        chart = (
            alt.Chart(chart_df)
            .mark_line(point=alt.OverlayMarkDef(size=80, filled=True))
            .encode(
                x=alt.X("Data:T", title="Data"),
                y=alt.Y(
                    "Carga:Q",
                    title="Carga máx. (kg)",
                    scale=alt.Scale(zero=False, padding=10),
                ),
                tooltip=[
                    alt.Tooltip("Data:T", title="Data", format="%d/%m/%Y %H:%M"),
                    alt.Tooltip("Carga:Q", title="Carga (kg)"),
                ],
            )
            .properties(height=360)
        )
        st.altair_chart(chart, use_container_width=True)
        st.caption("Carga máxima por execução (ignora séries com carga 0).")

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
        c for c in ["DataExecucao", "Carga", "Repeticoes", "Series", "Intervalo", "Observacoes"]
        if c in dados.columns
    ]
    st.dataframe(
        dados[cols_hist].rename(columns={"DataExecucao": "Data"}),
        hide_index=True,
        use_container_width=True,
    )


def main() -> None:
    st.title("💪 Evolução dos alunos")

    df_treinos = carregar_treinos()
    df_exec = carregar_execucoes()

    if df_treinos.empty:
        st.warning("Nenhum dado encontrado na aba Treinos.")
        return

    alunos = (
        df_treinos[["CodigoCliente", "NomeCliente"]]
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

    treino_atual = df_treinos[df_treinos["CodigoCliente"] == cod_sel]
    if treino_atual.empty:
        st.info("Aluno sem ficha de treino cadastrada.")
        return

    df_aluno_exec = (
        df_exec[df_exec["CodigoCliente"] == cod_sel]
        if not df_exec.empty
        else pd.DataFrame()
    )

    if not df_aluno_exec.empty:
        ultima_exec = df_aluno_exec["DataExecucao"].max()
        n_execs = df_aluno_exec[["TreinoId", "Sessao", "DataExecucao"]].drop_duplicates().shape[0]
        st.caption(
            f"Última execução: **{pd.Timestamp(ultima_exec).strftime('%d/%m/%Y %H:%M')}** · "
            f"{n_execs} execução(ões) no histórico"
        )
    else:
        st.caption("Sem execuções registradas ainda — o gráfico ficará vazio até a próxima sessão concluída.")

    col_treino, col_volume = st.columns([2, 1])

    with col_treino:
        st.subheader("Treino atual")
        sessoes = sorted(treino_atual["Sessao"].dropna().unique())
        if not sessoes:
            st.info("Sem sessões na ficha.")
        for sessao in sessoes:
            bloco = treino_atual[treino_atual["Sessao"] == sessao].copy()
            # Ordena pela ordem definida na ficha (OrdemExercicio)
            if "OrdemExercicio" in bloco.columns:
                bloco["_ordem"] = pd.to_numeric(bloco["OrdemExercicio"], errors="coerce")
                bloco = bloco.sort_values("_ordem", kind="stable", na_position="last")
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
                            if df_aluno_exec.empty:
                                df_ex = pd.DataFrame()
                            else:
                                df_ex = df_aluno_exec[
                                    (df_aluno_exec["Exercicio"] == ex["Exercicio"])
                                    & (df_aluno_exec["Sessao"] == sessao)
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
            carregar_treinos.clear()
            carregar_execucoes.clear()
            st.rerun()


if __name__ == "__main__":
    main()
