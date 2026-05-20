"""Sincroniza a aba 'Alunos' da planilha Controle Professores com o NextFit.

Cada execucao reescreve a aba inteira: ClienteId | Nome | Turno | Professor |
Status (ATIVO/INATIVO) | AtualizadoEm.

- Status ATIVO = cliente.inativo == False AND existe contrato com status='Ativo'
- Professor   = nome do usuario referenciado em cliente.codigoUsuarioProfessor
- Turno       = derivado do contrato (DescricaoModalidade) quando possivel,
                ou de heuristica simples; deixa em branco se nao der pra inferir.
                O professor pode editar manualmente na aba Alunos depois.

Uso:
    python -m controle_professores.sync_alunos
"""
from __future__ import annotations

import os
import sys
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from controle_professores.client import open_controle  # noqa: E402
from controle_professores.config import HEADERS_ALUNOS, TAB_ALUNOS  # noqa: E402
from nextfit_client import NextFitClient  # noqa: E402


def _is_ativo(cliente: dict, contratos_ativos_por_cliente: set) -> bool:
    cliente_sub = cliente.get("cliente") or {}
    inativo = cliente_sub.get("inativo")
    # campo `inativo` pode vir como bool ou string
    if isinstance(inativo, bool):
        is_inativo = inativo
    else:
        is_inativo = str(inativo).strip().upper() in {"TRUE", "VERDADEIRO", "1"}
    if is_inativo:
        return False
    return cliente.get("id") in contratos_ativos_por_cliente


def _inferir_turno(modalidades: list[str]) -> str:
    """Heuristica: olha o nome das modalidades/contratos pra inferir turno.
    So e usada como sugestao inicial quando o professor ainda nao preencheu.
    Devolve MANHÃ/TARDE/NOITE ou string vazia se nao deu.
    """
    texto = " ".join(modalidades).upper()
    if "MANH" in texto:
        return "MANHÃ"
    if "TARDE" in texto:
        return "TARDE"
    if "NOITE" in texto or "NOTURN" in texto:
        return "NOITE"
    return ""


def main() -> int:
    load_dotenv(PROJECT_ROOT / ".env")

    api_key = os.environ.get("NEXTFIT_API_KEY", "").strip()
    if not api_key:
        print("[erro] NEXTFIT_API_KEY ausente no .env", file=sys.stderr)
        return 1

    nf = NextFitClient(
        api_key=api_key,
        base_url=os.environ["NEXTFIT_BASE_URL"],
        version=os.environ.get("NEXTFIT_API_VERSION", "1"),
    )

    print("[sync_alunos] buscando clientes, usuarios e contratos do NextFit...")
    t0 = time.time()
    clientes = nf.clientes()
    usuarios = nf.usuarios()
    contratos = nf.contratos_cliente()
    print(
        f"  clientes={len(clientes)} usuarios={len(usuarios)} "
        f"contratos={len(contratos)} ({time.time()-t0:.1f}s)"
    )

    nome_por_usuario = {u.get("id"): (u.get("nome") or "").strip() for u in usuarios}

    # Preserva o Turno ja preenchido na aba (edicoes do professor no app).
    # A heuristica so vale como sugestao inicial pra quem ainda nao tem turno.
    sc = open_controle()
    turnos_existentes: dict[int, str] = {}
    for a in sc.read_tab_all(TAB_ALUNOS):
        try:
            cid_e = int(a.get("ClienteId"))
        except (TypeError, ValueError):
            continue
        t = str(a.get("Turno") or "").strip()
        if t:
            turnos_existentes[cid_e] = t

    # Mapeia cliente -> lista de modalidades dos contratos ativos
    contratos_ativos_por_cliente: set = set()
    modalidades_por_cliente: dict[int, list[str]] = {}
    for ct in contratos:
        if str(ct.get("status")).strip() != "Ativo":
            continue
        cod = ct.get("codigoCliente")
        if cod is None:
            continue
        contratos_ativos_por_cliente.add(cod)
        modalidades_por_cliente.setdefault(cod, []).append(
            (ct.get("descricaoContratoBase") or ct.get("descricaoModalidade") or "")
        )

    agora_iso = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    rows: list[dict] = []
    for c in clientes:
        cod = c.get("id")
        if cod is None:
            continue
        cliente_sub = c.get("cliente") or {}
        nome = (c.get("nome") or "").strip()
        if not nome:
            continue
        cod_prof = cliente_sub.get("codigoUsuarioProfessor")
        prof = nome_por_usuario.get(cod_prof, "") if cod_prof else ""
        ativo = _is_ativo(c, contratos_ativos_por_cliente)
        # Turno preenchido pelo professor manda; senao, sugestao da heuristica.
        turno = turnos_existentes.get(cod) or _inferir_turno(modalidades_por_cliente.get(cod, []))
        rows.append({
            "ClienteId": cod,
            "Nome": nome,
            "Turno": turno,
            "Professor": prof,
            "Status": "ATIVO" if ativo else "INATIVO",
            "AtualizadoEm": agora_iso,
        })

    # Ordena: ativos primeiro, depois por nome
    rows.sort(key=lambda r: (r["Status"] != "ATIVO", r["Nome"].lower()))

    print(f"[sync_alunos] gravando {len(rows)} linhas em '{TAB_ALUNOS}'...")
    # Usa write_tab pra reescrever inteira (idempotente). Reaproveita o `sc`
    # aberto acima (que leu os turnos existentes).
    written = sc.write_tab(TAB_ALUNOS, rows)
    ativos = sum(1 for r in rows if r["Status"] == "ATIVO")
    com_prof = sum(1 for r in rows if r["Status"] == "ATIVO" and r["Professor"])
    print(f"  [ok] {written} linhas escritas. Ativos: {ativos}. Com professor: {com_prof}.")

    # Resumo por professor
    from collections import Counter
    cnt = Counter(r["Professor"] for r in rows if r["Status"] == "ATIVO")
    print("[sync_alunos] alunos ativos por professor:")
    for prof, n in sorted(cnt.items(), key=lambda kv: -kv[1]):
        label = prof or "(sem professor)"
        print(f"  {label}: {n}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
