"""App administrativo — Retencao mensal por professor + ferramentas operacionais.

Layout:
- Hero: comparacao Mes A -> Mes B com 3 KPIs
- Tabela por professor: ativos, retidos (status + engajamento), receita, qualidade
- Drill-down expansivel por prof: quem foi perdido + quem esta em risco
- Acordeao "Ferramentas operacionais": sumico, queda, comparativo, historico

Para rodar:
    streamlit run dashboard/app_admin.py
"""
from __future__ import annotations

import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from controle_professores.client import get_config_int  # noqa: E402
from controle_professores.retencao import (  # noqa: E402
    BaseDados,
    alertas_sumico,
    alunos_recentes,
    carregar_tudo,
    comparativo_semana,
    historico_aluno,
    label_mes,
    periodo_mes,
    proximo_mes,
    queda_frequencia,
    retencao_comparativa,
    retencao_por_modalidade,
)
from controle_professores.treinos import (  # noqa: E402
    carregar_execucoes,
    metricas_cohort,
)
from controle_professores.semana import (  # noqa: E402
    fmt_iso,
    label_semana,
    semana_atual,
)


_ADMIN_CSS = """
    <style>
        .block-container { padding-top: 1.5rem; padding-bottom: 3rem; max-width: 1200px; }
        .kpi-card {
            background: linear-gradient(135deg, #ffffff 0%, #f5f7fa 100%);
            border: 1px solid #e1e4e8;
            border-radius: 12px;
            padding: 1.5rem;
            text-align: center;
            min-height: 140px;
        }
        .kpi-label {
            color: #6b7280;
            font-size: 0.85rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 0.5rem;
        }
        .kpi-value {
            font-size: 2.5rem;
            font-weight: 700;
            line-height: 1;
            color: #111827;
        }
        .kpi-sub {
            color: #6b7280;
            font-size: 0.85rem;
            margin-top: 0.5rem;
        }
        .kpi-sub-positive { color: #059669; }
        .kpi-sub-negative { color: #dc2626; }
        .badge {
            display: inline-block;
            padding: 2px 10px;
            border-radius: 999px;
            font-size: 0.85rem;
            font-weight: 600;
        }
        .badge-good { background: #d1fae5; color: #065f46; }
        .badge-warn { background: #fef3c7; color: #92400e; }
        .badge-bad  { background: #fee2e2; color: #991b1b; }
    </style>
    """


def _inject_css() -> None:
    """CSS do dashboard. Chamado por main() — assim nada roda no import,
    o que permite o app_professor importar este modulo e chamar main()."""
    st.markdown(_ADMIN_CSS, unsafe_allow_html=True)


@st.cache_data(ttl=180, show_spinner="Carregando dados...")
def _base() -> BaseDados:
    return carregar_tudo()


@st.cache_data(ttl=180, show_spinner="Carregando execucoes de treino...")
def _execucoes() -> list[dict]:
    return carregar_execucoes()


def _fmt_brl(v: float) -> str:
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _badge(taxa: float) -> str:
    if taxa >= 0.90:
        return f"<span class='badge badge-good'>🟢 {taxa*100:.1f}%</span>"
    if taxa >= 0.80:
        return f"<span class='badge badge-warn'>🟡 {taxa*100:.1f}%</span>"
    return f"<span class='badge badge-bad'>🔴 {taxa*100:.1f}%</span>"


def _gerar_opcoes_meses(meses_pra_tras: int = 12) -> list[tuple[int, int, str]]:
    """Gera lista de (ano, mes, label) ordenada do mais recente pro mais antigo."""
    hoje = date.today()
    out = []
    ano, mes = hoje.year, hoje.month
    for _ in range(meses_pra_tras):
        out.append((ano, mes, label_mes(ano, mes)))
        if mes == 1:
            ano, mes = ano - 1, 12
        else:
            mes -= 1
    return out


def _kpi_card(label: str, valor: str, sub: str = "", sub_class: str = "") -> str:
    sub_html = f"<div class='kpi-sub {sub_class}'>{sub}</div>" if sub else ""
    return (
        f"<div class='kpi-card'>"
        f"<div class='kpi-label'>{label}</div>"
        f"<div class='kpi-value'>{valor}</div>"
        f"{sub_html}"
        f"</div>"
    )


def _render_treinos_prof(linha, ano_m2: int, mes_m2: int, label_m2: str) -> None:
    """Aba 'Treinos & Progressao' no drill-down de cada professor."""
    inicio_m2, fim_m2 = periodo_mes(ano_m2, mes_m2)
    execucoes = _execucoes()
    if not execucoes:
        st.info("Sem execuções de treino registradas (aba HistoricoExecucoes vazia ou inexistente).")
        return

    m = metricas_cohort(
        cohort_ids=linha.cohort_ids,
        inicio=inicio_m2,
        fim=fim_m2,
        execucoes=execucoes,
        nome_por_cliente=linha.nome_por_cliente,
    )

    if m.sessoes_finalizadas == 0:
        st.info(
            f"Nenhuma sessão de treino concluída pelos alunos do(a) **{linha.professor}** em {label_m2}.\n\n"
            "Possíveis causas: ficha não cadastrada na NextFit, alunos não usam o app, ou o sync ainda não rodou."
        )
        return

    # KPIs de treino
    pct_treinaram = (m.alunos_com_execucao / m.cohort_size * 100) if m.cohort_size else 0
    cols = st.columns(4)
    cols[0].metric(
        "Sessões finalizadas",
        m.sessoes_finalizadas,
        f"{m.media_sessoes_por_aluno:.1f} por aluno ativo",
    )
    cols[1].metric(
        "Alunos que treinaram",
        f"{m.alunos_com_execucao}/{m.cohort_size}",
        f"{pct_treinaram:.1f}% do cohort",
    )
    cols[2].metric(
        "Volume total",
        f"{m.series_totais} séries",
        f"{m.media_series_por_sessao:.1f} séries/sessão",
    )

    # Progressao
    total_prog = m.exercicios_progrediram + m.exercicios_iguais + m.exercicios_regrediram
    if total_prog:
        pct_prog = m.exercicios_progrediram / total_prog * 100
        cols[3].metric(
            "Exercícios progrediram",
            f"{m.exercicios_progrediram}/{total_prog}",
            f"{pct_prog:.1f}% subiram carga",
        )
    else:
        cols[3].metric(
            "Exercícios progrediram",
            "—",
            "Sem dados de carga",
        )

    # Detalhe progressao
    if total_prog:
        st.markdown("##### Progressão de carga (exercícios com 2+ execuções no mês)")
        bar_cols = st.columns([1, 1, 1])
        bar_cols[0].markdown(
            f"<div style='background:#d1fae5; padding:12px; border-radius:8px; text-align:center;'>"
            f"<div style='font-size:1.6rem; font-weight:700; color:#065f46;'>{m.exercicios_progrediram}</div>"
            f"<div style='color:#065f46; font-size:0.85rem;'>📈 Subiram carga</div>"
            f"</div>",
            unsafe_allow_html=True,
        )
        bar_cols[1].markdown(
            f"<div style='background:#fef3c7; padding:12px; border-radius:8px; text-align:center;'>"
            f"<div style='font-size:1.6rem; font-weight:700; color:#92400e;'>{m.exercicios_iguais}</div>"
            f"<div style='color:#92400e; font-size:0.85rem;'>➡️ Iguais (estagnados)</div>"
            f"</div>",
            unsafe_allow_html=True,
        )
        bar_cols[2].markdown(
            f"<div style='background:#fee2e2; padding:12px; border-radius:8px; text-align:center;'>"
            f"<div style='font-size:1.6rem; font-weight:700; color:#991b1b;'>{m.exercicios_regrediram}</div>"
            f"<div style='color:#991b1b; font-size:0.85rem;'>📉 Caíram carga</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

    # Top alunos
    st.markdown("##### Top alunos do mês (mais sessões)")
    if m.top_alunos:
        df_top = pd.DataFrame(m.top_alunos).rename(columns={
            "Sessoes": "Sessões",
            "SeriesTotais": "Séries totais",
        })
        st.dataframe(
            df_top[["Nome", "Sessões", "Séries totais"]],
            hide_index=True,
            use_container_width=True,
        )

    # Quem nao treinou
    if m.sem_treinar:
        with st.expander(f"😴 Alunos do cohort que NÃO treinaram em {label_m2} ({len(m.sem_treinar)})"):
            df_sem = pd.DataFrame(m.sem_treinar)
            st.dataframe(df_sem[["Nome"]], hide_index=True, use_container_width=True)


# =================== TELA PRINCIPAL: RETENCAO =====================

def render_retencao(base: BaseDados) -> None:
    st.markdown("## 📊 Retenção mensal")
    st.caption("Quantos alunos do mês A continuaram ativos no mês B — e quanto disso vira receita preservada.")

    # Seletor de meses
    opcoes = _gerar_opcoes_meses(meses_pra_tras=14)
    label_to_tuple = {label: (ano, mes) for ano, mes, label in opcoes}

    col1, col2, col3 = st.columns([3, 3, 2])
    # default M1 = mês passado, M2 = mês atual
    label_default_m1 = opcoes[1][2] if len(opcoes) > 1 else opcoes[0][2]
    label_default_m2 = opcoes[0][2]
    with col1:
        sel_m1 = st.selectbox("De (mês A)", [o[2] for o in opcoes], index=[o[2] for o in opcoes].index(label_default_m1))
    with col2:
        sel_m2 = st.selectbox("Para (mês B)", [o[2] for o in opcoes], index=[o[2] for o in opcoes].index(label_default_m2))
    with col3:
        meta_default = get_config_int("META_PRESENCAS_MES", 8)
        meta = st.number_input(
            "Meta presenças/mês",
            min_value=1, max_value=31,
            value=meta_default,
            help="Usada pra retenção por engajamento (não afeta status).",
        )

    ano_m1, mes_m1 = label_to_tuple[sel_m1]
    ano_m2, mes_m2 = label_to_tuple[sel_m2]

    if (ano_m1, mes_m1) >= (ano_m2, mes_m2):
        st.warning("Escolha um mês A anterior ao mês B pra fazer a comparação.")
        return

    # Detecta mes B incompleto (mes corrente ou futuro) — escala meta proporcionalmente
    from controle_professores.retencao import periodo_mes
    inicio_m2, fim_m2 = periodo_mes(ano_m2, mes_m2)
    hoje = date.today()
    meta_efetiva = int(meta)
    mes_incompleto = False
    if hoje <= fim_m2:
        if hoje < inicio_m2:
            st.error(f"Mês B ({sel_m2}) está no futuro — comparação impossível.")
            return
        dias_passados = (hoje - inicio_m2).days + 1
        dias_total = (fim_m2 - inicio_m2).days + 1
        proporcao = dias_passados / dias_total
        meta_efetiva = max(1, round(meta * proporcao))
        mes_incompleto = True

    dados = retencao_comparativa(
        ano_m1, mes_m1, ano_m2, mes_m2,
        base=base, meta_presencas=meta_efetiva,
    )

    if mes_incompleto:
        st.info(
            f"📅 **{sel_m2} ainda não terminou** — só {dias_passados} de {dias_total} dias passaram "
            f"({proporcao*100:.0f}% do mês). A meta de engajamento foi escalada de **{int(meta)}** "
            f"para **{meta_efetiva}** presenças proporcionalmente."
        )

    if dados["total_ativos_m1"] == 0:
        st.info(f"Sem alunos ativos detectados em {sel_m1}. Verifique se a aba ContratosCliente está sincronizada.")
        return

    # =========== KPIs do topo ===========
    perdidos = dados["alunos_perdidos"]
    perdidos_pct = (perdidos / dados["total_ativos_m1"] * 100) if dados["total_ativos_m1"] else 0

    cols = st.columns(4)
    with cols[0]:
        st.markdown(_kpi_card(
            "Retenção (status)",
            f"{dados['taxa_status_total']*100:.1f}%",
            f"{dados['total_retidos_status']} de {dados['total_ativos_m1']} mantidos",
        ), unsafe_allow_html=True)
    with cols[1]:
        st.markdown(_kpi_card(
            "Retenção (engajamento)",
            f"{dados['taxa_engaj_total']*100:.1f}%",
            f"≥ {dados['meta_presencas']} presenças no mês B",
        ), unsafe_allow_html=True)
    with cols[2]:
        st.markdown(_kpi_card(
            "Receita preservada",
            _fmt_brl(dados["receita_preservada"]),
            f"de {_fmt_brl(dados['receita_inicial'])} inicial",
        ), unsafe_allow_html=True)
    with cols[3]:
        st.markdown(_kpi_card(
            "Alunos perdidos",
            f"{perdidos}",
            f"↓ {perdidos_pct:.1f}% da base",
            "kpi-sub-negative" if perdidos else "kpi-sub-positive",
        ), unsafe_allow_html=True)

    st.markdown("###### Status × Engajamento")
    gap = dados["taxa_status_total"] - dados["taxa_engaj_total"]
    if gap > 0.05:
        st.warning(
            f"⚠️ Gap de **{gap*100:.1f} p.p.** entre status e engajamento — "
            f"existem alunos com contrato ativo mas que não estão treinando o suficiente."
        )
    else:
        st.success("Status e engajamento andam juntos — base saudável.")

    st.divider()

    # =========== Tabela por professor ===========
    st.markdown("### Por professor")
    linhas = dados["linhas_prof"]
    if not linhas:
        st.info("Sem dados por professor.")
        return

    # Header da tabela
    head = st.columns([3, 1, 1.2, 1.2, 1.5, 1.2])
    head[0].markdown("**Professor**")
    head[1].markdown("**Início → Fim**")
    head[2].markdown("**Status**")
    head[3].markdown("**Engaj.**")
    head[4].markdown("**Receita**")
    head[5].markdown("**Qualidade**")
    st.markdown("<hr style='margin: 4px 0; border: none; border-top: 1px solid #e1e4e8;'>", unsafe_allow_html=True)

    for linha in linhas:
        # Linha resumo
        cols_l = st.columns([3, 1, 1.2, 1.2, 1.5, 1.2])
        cols_l[0].markdown(f"**{linha.professor}**")
        cols_l[1].markdown(f"{linha.ativos_m1} → {linha.retidos_status}")
        cols_l[2].markdown(_badge(linha.taxa_status), unsafe_allow_html=True)
        cols_l[3].markdown(_badge(linha.taxa_engajamento), unsafe_allow_html=True)
        cols_l[4].markdown(_fmt_brl(linha.receita_preservada))
        # Qualidade: barra simples
        qual_pct = linha.qualidade_registro * 100
        qual_color = "#059669" if qual_pct >= 80 else "#d97706" if qual_pct >= 50 else "#dc2626"
        cols_l[5].markdown(
            f"<div style='display:flex; align-items:center; gap:8px;'>"
            f"<div style='flex:1; background:#e5e7eb; border-radius:4px; height:8px;'>"
            f"<div style='width:{qual_pct:.0f}%; background:{qual_color}; height:100%; border-radius:4px;'></div>"
            f"</div><span style='font-size:0.85rem; color:#6b7280;'>{qual_pct:.0f}%</span></div>",
            unsafe_allow_html=True,
        )

        # Drill-down do professor
        with st.expander(f"Ver detalhe de {linha.professor}", expanded=False):
            tab_perd, tab_risco, tab_treinos = st.tabs([
                f"❌ Perdidos ({len(linha.perdidos)})",
                f"⚠️ Em risco ({len(linha.em_risco)})",
                "🏋️ Treinos & Progressão",
            ])
            with tab_perd:
                if not linha.perdidos:
                    st.success("Nenhum aluno perdido nesse período. 🎉")
                else:
                    df_perd = pd.DataFrame(linha.perdidos)
                    df_perd = df_perd.rename(columns={
                        "Nome": "Aluno",
                        "PresencasM2": f"Presenças em {dados['label_m2']}",
                        "ValorM1": f"Mensalidade em {dados['label_m1']}",
                    })
                    df_perd[f"Mensalidade em {dados['label_m1']}"] = df_perd[f"Mensalidade em {dados['label_m1']}"].apply(_fmt_brl)
                    st.dataframe(
                        df_perd[["Aluno", f"Presenças em {dados['label_m2']}", f"Mensalidade em {dados['label_m1']}"]],
                        hide_index=True,
                        use_container_width=True,
                    )
            with tab_risco:
                if not linha.em_risco:
                    st.success(f"Nenhum aluno ativo abaixo da meta ({dados['meta_presencas']}) em {dados['label_m2']}.")
                else:
                    df_risco = pd.DataFrame(linha.em_risco)
                    df_risco = df_risco.rename(columns={
                        "Nome": "Aluno",
                        "PresencasM2": f"Presenças em {dados['label_m2']}",
                        "MetaM2": "Meta",
                    })
                    st.caption("Alunos com contrato ATIVO em B mas presenças abaixo da meta — alvo do prof na próxima semana.")
                    st.dataframe(
                        df_risco[["Aluno", f"Presenças em {dados['label_m2']}", "Meta"]],
                        hide_index=True,
                        use_container_width=True,
                    )
            with tab_treinos:
                _render_treinos_prof(linha, ano_m2, mes_m2, dados['label_m2'])

        st.markdown("<hr style='margin: 4px 0; border: none; border-top: 1px solid #f3f4f6;'>", unsafe_allow_html=True)


def render_retencao_modalidade(base: BaseDados) -> None:
    st.markdown("## 📦 Retenção por modalidade")
    st.caption(
        "Mesma lógica da retenção mensal, agrupada pela modalidade do aluno no mês A "
        "(cada aluno entra uma vez, no plano de maior valor)."
    )

    opcoes = _gerar_opcoes_meses(meses_pra_tras=14)
    label_to_tuple = {label: (ano, mes) for ano, mes, label in opcoes}
    labels = [o[2] for o in opcoes]
    label_default_m1 = opcoes[1][2] if len(opcoes) > 1 else opcoes[0][2]
    label_default_m2 = opcoes[0][2]

    c1, c2, c3 = st.columns([3, 3, 2])
    with c1:
        sel_m1 = st.selectbox("De (mês A)", labels, index=labels.index(label_default_m1), key="mod_m1")
    with c2:
        sel_m2 = st.selectbox("Para (mês B)", labels, index=labels.index(label_default_m2), key="mod_m2")
    with c3:
        agrupar_label = st.radio("Agrupar por", ["Categoria", "Plano detalhado"], key="mod_agrupar")
    agrupar = "categoria" if agrupar_label == "Categoria" else "plano"

    ano_m1, mes_m1 = label_to_tuple[sel_m1]
    ano_m2, mes_m2 = label_to_tuple[sel_m2]
    if (ano_m1, mes_m1) >= (ano_m2, mes_m2):
        st.warning("Escolha um mês A anterior ao mês B pra fazer a comparação.")
        return

    dados = retencao_por_modalidade(ano_m1, mes_m1, ano_m2, mes_m2, base=base, agrupar=agrupar)
    if dados["total_ativos_m1"] == 0:
        st.info(f"Sem alunos ativos detectados em {sel_m1}.")
        return

    perdidos_tot = dados["total_ativos_m1"] - dados["total_retidos_status"]
    cols = st.columns(4)
    with cols[0]:
        st.markdown(_kpi_card(
            "Retenção geral",
            f"{dados['taxa_status_total']*100:.1f}%",
            f"{dados['total_retidos_status']} de {dados['total_ativos_m1']} mantidos",
        ), unsafe_allow_html=True)
    with cols[1]:
        st.markdown(_kpi_card(
            "Receita preservada",
            _fmt_brl(dados["receita_preservada"]),
            f"de {_fmt_brl(dados['receita_inicial'])} inicial",
            "kpi-sub-positive",
        ), unsafe_allow_html=True)
    with cols[2]:
        st.markdown(_kpi_card(
            "Receita perdida",
            _fmt_brl(dados["receita_perdida"]),
            f"mensalidade de quem saiu ({sel_m1})",
            "kpi-sub-negative" if dados["receita_perdida"] else "kpi-sub-positive",
        ), unsafe_allow_html=True)
    with cols[3]:
        st.markdown(_kpi_card(
            "Alunos perdidos",
            f"{perdidos_tot}",
            f"{sel_m1} → {sel_m2}",
            "kpi-sub-negative" if perdidos_tot else "kpi-sub-positive",
        ), unsafe_allow_html=True)

    st.markdown(f"### Por modalidade · {dados['label_m1']} → {dados['label_m2']}")
    linhas = dados["linhas"]
    if not linhas:
        st.info("Sem modalidades detectadas.")
        return

    larguras = [2.6, 1.3, 1.0, 1.5, 1.5]
    head = st.columns(larguras)
    head[0].markdown("**Modalidade**")
    head[1].markdown("**Ativos → Retidos**")
    head[2].markdown("**Taxa**")
    head[3].markdown("**Receita preservada**")
    head[4].markdown("**Receita perdida**")
    st.markdown("<hr style='margin: 4px 0; border: none; border-top: 1px solid #e1e4e8;'>", unsafe_allow_html=True)

    for l in linhas:
        cl = st.columns(larguras)
        cl[0].markdown(f"**{l.modalidade}**")
        cl[1].markdown(f"{l.ativos_m1} → {l.retidos_status}")
        cl[2].markdown(_badge(l.taxa_status), unsafe_allow_html=True)
        cl[3].markdown(_fmt_brl(l.receita_preservada))
        cl[4].markdown(f"<span style='color:#dc2626;'>{_fmt_brl(l.receita_perdida)}</span>", unsafe_allow_html=True)

        if l.perdidos:
            with st.expander(f"❌ {len(l.perdidos)} perdido(s) em {l.modalidade}", expanded=False):
                df = pd.DataFrame([
                    {"Aluno": p["Nome"], f"Mensalidade em {dados['label_m1']}": _fmt_brl(p["ValorM1"])}
                    for p in l.perdidos
                ])
                st.dataframe(df, hide_index=True, use_container_width=True)
        st.markdown("<hr style='margin: 4px 0; border: none; border-top: 1px solid #f3f4f6;'>", unsafe_allow_html=True)


# =================== FERRAMENTAS OPERACIONAIS =====================

def render_acompanhamento(base: BaseDados) -> None:
    """Acompanhamento de presenca — modos: ativos recentes (default) ou sumidos (ate X)."""
    modo = st.radio(
        "Modo",
        options=[
            "Ativos recentes (vieram há menos de X dias)",
            "Sumidos (com até X dias de falta)",
        ],
        index=0,
        horizontal=False,
        key="modo_pres",
    )
    eh_sumico = modo.startswith("Sumidos")
    dias_default = 7 if not eh_sumico else get_config_int("DIAS_SUMICO_ALERTA", 14)
    dias = st.slider("X dias", 1, 60, dias_default, key="dias_pres")

    if eh_sumico:
        dados = alertas_sumico(base=base, dias=int(dias), modo="max")
        if not dados:
            st.info(f"Nenhum aluno ativo com até {dias} dias de falta.")
            return
        st.warning(f"{len(dados)} aluno(s) com até {dias} dia(s) de falta — quanto mais perto do limite, mais perto de sumir.")
        df = pd.DataFrame(dados)
        st.dataframe(
            df[["Professor", "Nome", "UltimoAcesso", "DiasSemVir"]].rename(
                columns={"DiasSemVir": "Dias de falta"}
            ),
            hide_index=True,
            use_container_width=True,
        )
        from collections import Counter
        cnt = Counter(d["Professor"] or "(sem prof)" for d in dados)
        st.markdown("**Por professor:**")
        st.dataframe(
            pd.DataFrame([{"Professor": p, "Alunos": n} for p, n in cnt.most_common()]),
            hide_index=True, use_container_width=True,
        )
    else:
        dados = alunos_recentes(base=base, dias=int(dias))
        if not dados:
            st.info(f"Nenhum aluno ativo apareceu nos últimos {dias} dias.")
            return
        st.success(f"{len(dados)} aluno(s) treinaram nos últimos {dias} dias.")
        df = pd.DataFrame(dados)
        st.dataframe(
            df[["Professor", "Nome", "UltimoAcesso", "DiasDesdeUltimo"]].rename(
                columns={"DiasDesdeUltimo": "Há X dias"}
            ),
            hide_index=True,
            use_container_width=True,
        )
        from collections import Counter
        cnt = Counter(d["Professor"] or "(sem prof)" for d in dados)
        st.markdown("**Por professor:**")
        st.dataframe(
            pd.DataFrame([{"Professor": p, "Treinaram": n} for p, n in cnt.most_common()]),
            hide_index=True, use_container_width=True,
        )


def render_queda(base: BaseDados) -> None:
    n_sem = st.slider("Comparar últimas N semanas vs N anteriores", 2, 8, 4, key="queda_n")
    dados = queda_frequencia(base=base, semanas_compara=int(n_sem))
    if not dados:
        st.success("Nenhum aluno com queda significativa de frequência.")
        return
    st.warning(f"{len(dados)} aluno(s) com queda ≥ 1 presença/semana.")
    df = pd.DataFrame(dados)
    st.dataframe(
        df[["Professor", "Nome", "MediaAnterior", "MediaRecente", "Delta"]],
        hide_index=True,
        use_container_width=True,
    )


def render_comparativo(base: BaseDados) -> None:
    sem_ini_atual, _ = semana_atual()
    opts: list[tuple[str, date]] = []
    for k in range(12):
        ini = sem_ini_atual - timedelta(days=7 * k)
        fim = ini + timedelta(days=6)
        label = f"{label_semana(ini, fim)} ({fmt_iso(ini)})"
        opts.append((label, ini))
    sel_label = st.selectbox("Semana", [o[0] for o in opts], key="cmp_semana")
    sem_ini = next(ini for label, ini in opts if label == sel_label)

    dados = comparativo_semana(sem_ini, base=base)
    if not dados:
        st.info(f"Sem registros para a semana {label_semana(sem_ini, sem_ini + timedelta(days=6))}.")
        return

    df = pd.DataFrame(dados)
    def _flag(row):
        d = row["Diferenca"]
        if d is None:
            return "❓ Não digitou número"
        if abs(d) <= 1:
            return "✅ OK"
        if d > 0:
            return f"⚠️ Marcou +{d} a mais"
        return f"⚠️ Marcou {d} a menos"
    df["Status"] = df.apply(_flag, axis=1)

    st.dataframe(
        df[["Professor", "Nome", "FreqDigitada", "FreqReal", "Diferenca", "Status"]],
        hide_index=True,
        use_container_width=True,
    )

    st.divider()
    st.markdown("**Resumo por professor:**")
    resumo = []
    for prof, sub in df.groupby("Professor"):
        total = len(sub)
        divergencias = sum(1 for d in sub["Diferenca"] if d is not None and abs(d) > 1)
        sem_numero = sum(1 for d in sub["Diferenca"] if d is None)
        resumo.append({
            "Professor": prof or "(sem prof)",
            "Alunos registrados": total,
            "Divergências (>1)": divergencias,
            "Sem número": sem_numero,
        })
    st.dataframe(pd.DataFrame(resumo), hide_index=True, use_container_width=True)


def render_historico(base: BaseDados) -> None:
    nomes = sorted(
        [(a.get("Nome", ""), a.get("ClienteId")) for a in base.alunos
         if str(a.get("Status")).strip().upper() == "ATIVO"
         and a.get("Nome")],
        key=lambda t: t[0].lower(),
    )
    if not nomes:
        st.info("Sem alunos ativos.")
        return
    nome_sel = st.selectbox("Aluno", [n[0] for n in nomes], key="hist_aluno")
    cid = next(n[1] for n in nomes if n[0] == nome_sel)
    try:
        cid_int = int(cid)
    except (TypeError, ValueError):
        st.error("ClienteId inválido.")
        return

    hist = historico_aluno(cid_int, base=base)
    aluno = hist["Aluno"]
    st.markdown(
        f"**{aluno.get('Nome', '?')}** · "
        f"Professor: {aluno.get('Professor') or '(sem prof)'} · "
        f"Turno: {aluno.get('Turno') or '?'} · "
        f"Status: {aluno.get('Status') or '?'}"
    )
    timeline = hist["Timeline"]
    if not timeline:
        st.info("Sem registros semanais para este aluno.")
        return

    df = pd.DataFrame(timeline)
    st.dataframe(
        df[["SemanaInicio", "SemanaFim", "FreqDigitada", "FreqReal", "Desempenho", "Relato", "AtualizadoEm"]],
        hide_index=True,
        use_container_width=True,
    )


# =========================== MAIN =================================

def main() -> None:
    _inject_css()
    base = _base()

    # Topbar com refresh
    head_l, head_r = st.columns([5, 1])
    head_l.title("🛠️ Admin · Controle Professores")
    if head_r.button("🔄 Recarregar", use_container_width=True):
        _base.clear()
        st.rerun()

    render_retencao(base)

    st.divider()

    render_retencao_modalidade(base)

    st.divider()

    st.markdown("## 🔧 Ferramentas operacionais")
    st.caption("Auditoria de qualidade do registro, alertas operacionais e busca individual.")

    with st.expander("👥 Acompanhamento de presença (ativos recentes / sumidos)", expanded=False):
        render_acompanhamento(base)

    with st.expander("📉 Queda de frequência — alerta de risco", expanded=False):
        render_queda(base)

    with st.expander("👀 Digitada × Real — qualidade do registro do prof", expanded=False):
        render_comparativo(base)

    with st.expander("👤 Histórico individual do aluno", expanded=False):
        render_historico(base)


if __name__ == "__main__":
    st.set_page_config(
        page_title="Admin · Retenção",
        page_icon="📊",
        layout="wide",
    )
    main()
