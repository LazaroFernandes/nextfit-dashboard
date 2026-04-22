"""Lista execuções recentes em HistoricoExecucoes agrupadas por aluno + sessão."""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from dotenv import load_dotenv

from sheets_client import SheetsClient

ENV_PATH = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(ENV_PATH)


def main() -> None:
    sheets = SheetsClient(
        credentials_file=os.environ["GOOGLE_CREDENTIALS_FILE"],
        sheet_id=os.environ["GOOGLE_SHEET_ID"],
    )
    rows = sheets.read_tab_all("HistoricoExecucoes")
    if not rows:
        print("HistoricoExecucoes vazia.")
        return

    grupos: dict[tuple, list[dict]] = {}
    for r in rows:
        key = (
            r.get("NomeCliente") or "",
            r.get("CodigoCliente"),
            r.get("SessaoExecutada") or r.get("Sessao"),
            r.get("TimestampExecucao") or r.get("DataCaptura"),
        )
        grupos.setdefault(key, []).append(r)

    # Agrupa execuções únicas por aluno
    execs_por_aluno: dict[tuple, set] = {}
    for (nome, codigo, sessao, ts), _ in grupos.items():
        execs_por_aluno.setdefault((nome, codigo), set()).add((sessao, ts))

    print("=" * 70)
    print("EXECUÇÕES POR ALUNO (quantas sessões cada um concluiu)")
    print("=" * 70)
    for (nome, codigo), sessoes in sorted(execs_por_aluno.items(), key=lambda x: -len(x[1])):
        print(f"  {len(sessoes):2d}x  {nome} (#{codigo})")
        for sessao, ts in sorted(sessoes, key=lambda x: x[1] or ""):
            print(f"           - sessão {sessao} em {ts}")

    print()
    print("=" * 70)
    print("DETALHE POR EXECUÇÃO")
    print("=" * 70)
    for (nome, codigo, sessao, ts), exercicios in sorted(grupos.items(), key=lambda x: x[0][3] or ""):
        print(f"{ts}  {nome} (#{codigo})  sessão {sessao}  {len(exercicios)} exercícios")
        for ex in exercicios:
            carga = ex.get("Carga") or "-"
            print(f"    · {ex.get('Exercicio')}  [{carga}]")


if __name__ == "__main__":
    main()
