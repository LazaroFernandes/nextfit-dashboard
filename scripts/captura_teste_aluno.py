"""Captura um novo snapshot de treino apenas para um aluno específico.

Uso de teste: popular o histórico com um 2º ponto pra visualizar o gráfico
de evolução no dashboard.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from dotenv import load_dotenv

from nextfit_v2_client import NextFitV2Client
from sheets_client import SheetsClient

ENV_PATH = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(ENV_PATH)


def main() -> None:
    if len(sys.argv) < 2:
        print("Uso: python scripts/captura_teste_aluno.py <codigo_aluno>")
        sys.exit(1)
    codigo_aluno = int(sys.argv[1])
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

    rows = v2.treinos_completos(clientes_ativos={codigo_aluno})
    print(f"Linhas capturadas para aluno {codigo_aluno}: {len(rows)}")
    if not rows:
        print("Aluno não tem treino ativo — nada a inserir.")
        return

    nome = rows[0].get("NomeCliente")
    data = rows[0].get("DataCaptura")
    print(f"Aluno: {nome} · Data da captura: {data}")

    escritas = sheets.append_tab("HistoricoTreinos", rows)
    print(f"Linhas adicionadas em HistoricoTreinos: {escritas}")


if __name__ == "__main__":
    main()
