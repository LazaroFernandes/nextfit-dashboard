"""App Streamlit (mobile-first) para os professores preencherem
frequencia / desempenho / relato dos alunos da semana.

Para rodar local na maquina da academia (acesso via celular pela rede):
    streamlit run dashboard/app_professor.py --server.address 0.0.0.0 --server.port 8501

Os outros computadores/celulares acessam via http://IP_DA_MAQUINA:8501
"""
from __future__ import annotations

import os
import sys
from datetime import date, timedelta
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from controle_professores.abrir_semana import abrir_semana  # noqa: E402
from controle_professores.alunos import set_turno  # noqa: E402
from controle_professores.client import open_controle  # noqa: E402
from controle_professores.config import TAB_ALUNOS, TAB_REGISTRO  # noqa: E402
from controle_professores.registro import upsert_em_lote  # noqa: E402
from controle_professores.semana import (  # noqa: E402
    fmt_iso,
    fmt_pt,
    label_semana,
    semana_atual,
    semana_de,
)


st.set_page_config(
    page_title="Registro Semanal",
    page_icon="📋",
    layout="centered",  # mobile-first
)

# CSS pra deixar inputs/cards mais friendly no mobile
st.markdown(
    """
    <style>
        .block-container { padding-top: 1rem; padding-bottom: 4rem; max-width: 720px; }
        .stButton > button { height: 44px; font-weight: 600; }
        .stTextArea textarea { min-height: 80px; }
        div[data-testid="stExpander"] summary { font-size: 1rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ----------------------------- Carregamento -----------------------------------

@st.cache_data(ttl=120, show_spinner="Carregando alunos...")
def carregar_alunos() -> list[dict]:
    sc = open_controle()
    return sc.read_tab_all(TAB_ALUNOS)


@st.cache_data(ttl=120, show_spinner="Carregando registros...")
def carregar_registros() -> list[dict]:
    sc = open_controle()
    return sc.read_tab_all(TAB_REGISTRO)


def _professores_disponiveis(alunos: list[dict]) -> list[str]:
    s = set()
    for a in alunos:
        if str(a.get("Status")).strip().upper() == "ATIVO":
            p = str(a.get("Professor") or "").strip()
            if p:
                s.add(p)
    return sorted(s)


def _alunos_do_prof(alunos: list[dict], prof: str) -> list[dict]:
    return sorted(
        [a for a in alunos
         if str(a.get("Status")).strip().upper() == "ATIVO"
         and str(a.get("Professor") or "").strip() == prof],
        key=lambda a: str(a.get("Nome") or "").lower(),
    )


def _registros_da_semana(
    registros: list[dict], prof: str, semana_ini: date,
) -> dict[int, dict]:
    """Indexa registros (ClienteId -> linha) da semana e do professor."""
    chave = fmt_iso(semana_ini)
    out: dict[int, dict] = {}
    for r in registros:
        if str(r.get("Professor") or "").strip() != prof:
            continue
        if str(r.get("SemanaInicio") or "").strip() != chave:
            continue
        try:
            cid = int(r["ClienteId"])
        except (KeyError, TypeError, ValueError):
            continue
        out[cid] = r
    return out


# ----------------------------- UI ---------------------------------------------

DESEMPENHOS = ["", "Muito bom", "Bom", "Regular", "Não está vindo", "Férias"]
TURNOS = ["", "MANHÃ", "TARDE", "NOITE"]


def _norm(s: str) -> str:
    return str(s or "").strip().casefold()


def _senha_master() -> str:
    """APP_PASSWORD: senha-mestra opcional que libera escolher qualquer professor."""
    try:
        v = st.secrets.get("APP_PASSWORD")
        if v:
            return str(v)
    except Exception:
        pass
    return os.environ.get("APP_PASSWORD", "").strip()


def _senhas_professores() -> dict[str, str]:
    """Mapa {nome_do_professor: senha} vindo da secao [senhas_professores] dos Secrets."""
    try:
        sec = st.secrets.get("senhas_professores")
        if sec:
            return {str(k): str(v) for k, v in dict(sec).items()}
    except Exception:
        pass
    return {}


def _logout() -> None:
    for k in ("_auth_ok", "_prof_login", "prof"):
        st.session_state.pop(k, None)
    st.rerun()


def _autenticado() -> bool:
    """Gate de senha.

    - [senhas_professores] nos Secrets: cada professor tem sua senha; ao entrar
      fica travado nos proprios alunos (st.session_state._prof_login).
    - APP_PASSWORD (opcional): senha-mestra que libera escolher qualquer professor.
    - Nenhuma configurada: acesso livre (dev local).
    """
    senhas = _senhas_professores()
    master = _senha_master()
    if not senhas and not master:
        return True
    if st.session_state.get("_auth_ok"):
        return True

    st.title("📋 Registro Semanal")
    st.caption("Acesso restrito aos professores.")
    senha = st.text_input("Senha", type="password", key="_senha_input")
    if st.button("Entrar", use_container_width=True):
        # 1) senha individual de um professor -> trava nele
        for nome, pw in senhas.items():
            if pw and senha == pw:
                st.session_state._auth_ok = True
                st.session_state._prof_login = nome
                st.rerun()
        # 2) senha-mestra -> acesso a todos (sem trava)
        if master and senha == master:
            st.session_state._auth_ok = True
            st.session_state._prof_login = None
            st.rerun()
        st.error("Senha incorreta.")
    return False


def main() -> None:
    if not _autenticado():
        return

    st.title("📋 Registro Semanal")

    alunos = carregar_alunos()
    if not alunos:
        st.warning(
            "Nenhum aluno cadastrado ainda. Rode "
            "`python -m controle_professores.sync_alunos` para sincronizar do NextFit."
        )
        return

    profs = _professores_disponiveis(alunos)
    if not profs:
        st.error("Nenhum professor encontrado entre os alunos ativos.")
        return

    # Persiste a semana entre interacoes
    if "semana_ini" not in st.session_state:
        st.session_state.semana_ini = semana_atual()[0]

    # Linha 1: professor — travado quando entrou com senha individual
    prof_login = st.session_state.get("_prof_login")
    if prof_login:
        prof = next((p for p in profs if _norm(p) == _norm(prof_login)), None)
        if prof is None:
            st.info(f"👤 **{prof_login}** — você não tem alunos ativos no momento.")
            if st.button("Sair"):
                _logout()
            return
        col_p, col_s = st.columns([4, 1])
        col_p.markdown(f"👤 Professor: **{prof}**")
        if col_s.button("Sair", use_container_width=True):
            _logout()
    else:
        if st.session_state.get("prof") not in profs:
            st.session_state.prof = profs[0]
        prof_idx = profs.index(st.session_state.prof)
        prof = st.selectbox("Professor", profs, index=prof_idx, key="prof")

    # Linha 2: semana — botoes ◀ ▶ + dropdown de semanas pertos
    col_l, col_m, col_r = st.columns([1, 4, 1])
    if col_l.button("◀", use_container_width=True, help="Semana anterior"):
        st.session_state.semana_ini = st.session_state.semana_ini - timedelta(days=7)
        st.rerun()
    if col_r.button("▶", use_container_width=True, help="Semana seguinte"):
        st.session_state.semana_ini = st.session_state.semana_ini + timedelta(days=7)
        st.rerun()
    sem_ini = st.session_state.semana_ini
    sem_fim = sem_ini + timedelta(days=6)
    col_m.markdown(
        f"<div style='text-align:center; font-size:1.1rem; padding-top:8px;'>"
        f"<b>{label_semana(sem_ini, sem_fim)}</b><br>"
        f"<span style='color:#666; font-size:0.9rem;'>{fmt_iso(sem_ini)} a {fmt_iso(sem_fim)}</span>"
        f"</div>",
        unsafe_allow_html=True,
    )

    st.divider()

    registros = carregar_registros()
    reg_idx = _registros_da_semana(registros, prof, sem_ini)
    alunos_prof = _alunos_do_prof(alunos, prof)

    # Se a semana nao foi aberta para esse prof, mostra botao
    sem_registros = len(reg_idx) == 0
    semana_eh_atual = sem_ini == semana_atual()[0]
    if sem_registros:
        st.info(
            f"Semana **{label_semana(sem_ini, sem_fim)}** ainda não foi aberta. "
            f"Clique abaixo para criar as linhas dos seus alunos ativos."
        )
        if st.button(
            "🔓 Abrir esta semana",
            type="primary",
            use_container_width=True,
        ):
            with st.spinner("Criando linhas da semana..."):
                ativos, novas = abrir_semana(sem_ini, professor_filtro=prof)
            st.success(f"{novas} linhas criadas (de {ativos} alunos ativos).")
            carregar_registros.clear()
            st.rerun()
        return

    # Resumo do topo. Trata 0 (int/string) como preenchido — diferente de "" (vazio).
    def _str_campo(reg: dict, campo: str) -> str:
        v = reg.get(campo)
        if v is None:
            return ""
        return str(v).strip()

    def _esta_preenchido(reg: dict) -> bool:
        return bool(
            _str_campo(reg, "Frequencia")
            or _str_campo(reg, "Desempenho")
            or _str_campo(reg, "Relato")
        )

    total = len(alunos_prof)
    preenchidos_total = 0
    for a in alunos_prof:
        try:
            cid = int(a["ClienteId"])
        except (KeyError, TypeError, ValueError):
            continue
        if _esta_preenchido(reg_idx.get(cid, {})):
            preenchidos_total += 1
    cols = st.columns(3)
    cols[0].metric("Alunos", total)
    cols[1].metric("Preenchidos", preenchidos_total)
    cols[2].metric("Pendentes", total - preenchidos_total)

    # Filtro: ver todos / so pendentes / so preenchidos
    filtro = st.radio(
        "Filtrar",
        options=["Todos", "Pendentes", "Preenchidos"],
        index=0,
        horizontal=True,
        label_visibility="collapsed",
    )

    st.divider()

    # Lista de alunos como expanders (clica no nome -> abre os campos)
    for a in alunos_prof:
        try:
            cid = int(a["ClienteId"])
        except (KeyError, TypeError, ValueError):
            continue
        r = reg_idx.get(cid, {})
        nome = a.get("Nome", "")
        turno = (a.get("Turno") or "").strip()
        preenchido = _esta_preenchido(r)

        if filtro == "Pendentes" and preenchido:
            continue
        if filtro == "Preenchidos" and not preenchido:
            continue

        check = "✅" if preenchido else "⬜"
        # Resumo do que ja foi preenchido pra mostrar no header fechado
        partes_resumo = []
        freq_atual = _str_campo(r, "Frequencia")
        desempenho_atual = _str_campo(r, "Desempenho")
        relato_atual = _str_campo(r, "Relato")
        if freq_atual:
            partes_resumo.append(f"Freq: {freq_atual}")
        if desempenho_atual:
            partes_resumo.append(desempenho_atual)
        resumo_inline = " · ".join(partes_resumo) if partes_resumo else ""
        turno_tag = f" · {turno}" if turno else ""

        # Header: check + nome + (turno) + (resumo se preenchido)
        header = f"{check}  **{nome}**{turno_tag}"
        if resumo_inline:
            header += f"  —  _{resumo_inline}_"

        with st.expander(header, expanded=False):
            # Turno: atributo do aluno (vale pra todas as semanas)
            turno_opcoes = list(TURNOS)
            if turno and turno not in turno_opcoes:
                turno_opcoes.append(turno)
            turno_input = st.selectbox(
                "Turno",
                options=turno_opcoes,
                index=turno_opcoes.index(turno) if turno in turno_opcoes else 0,
                key=f"turno_{cid}",
                help="Fica salvo para todas as semanas.",
            )
            freq_input = st.text_input(
                "Frequência",
                value=freq_atual,
                key=f"freq_{cid}",
                help="Ex.: 3, 5, 'Não está vindo', 'Férias'",
            )
            desempenho_input = st.selectbox(
                "Desempenho",
                options=DESEMPENHOS,
                index=DESEMPENHOS.index(desempenho_atual) if desempenho_atual in DESEMPENHOS else 0,
                key=f"des_{cid}",
            )
            relato_input = st.text_area(
                "Relato",
                value=relato_atual,
                key=f"rel_{cid}",
                placeholder="Como está sendo o treino, dificuldades, dores, evolução...",
            )

            mudou_registro = (
                freq_input != freq_atual
                or desempenho_input != desempenho_atual
                or relato_input != relato_atual
            )
            mudou_turno = (turno_input or "") != (turno or "")
            mudou = mudou_registro or mudou_turno
            if st.button(
                "💾 Salvar" if mudou else "✓ Sem alterações",
                key=f"save_{cid}",
                type="primary" if mudou else "secondary",
                use_container_width=True,
                disabled=not mudou,
            ):
                with st.spinner("Salvando..."):
                    if mudou_registro:
                        upsert_em_lote([{
                            "ClienteId": cid,
                            "Nome": nome,
                            "Professor": prof,
                            "SemanaInicio": fmt_iso(sem_ini),
                            "SemanaFim": fmt_iso(sem_fim),
                            "Frequencia": freq_input,
                            "Desempenho": desempenho_input,
                            "Relato": relato_input,
                        }])
                    if mudou_turno:
                        set_turno(cid, turno_input)
                        carregar_alunos.clear()
                carregar_registros.clear()
                st.toast(f"✅ {nome} salvo", icon="💾")
                st.rerun()


if __name__ == "__main__":
    main()
