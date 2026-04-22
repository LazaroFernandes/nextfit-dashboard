"""Cria um ponto histórico fictício em HistoricoExecucoes pra testar o dashboard.

Pega a última execução registrada de um aluno+sessão, duplica com timestamp
recuado (-7 dias) e cargas reduzidas ~15% — simulando progressão real.

Uso:
    python scripts/seed_ponto_ficticio.py <codigo_cliente> <sessao>

Ex: python scripts/seed_ponto_ficticio.py 25349096 1
"""
from __future__ import annotations

import os
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from dotenv import load_dotenv

from sheets_client import SheetsClient

ENV_PATH = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(ENV_PATH)


def _reduzir_carga(carga_str, fator: float = 0.85) -> str:
    """Multiplica cada número de uma string 'A/B/C' por `fator` (arredondando)."""
    carga_str = str(carga_str) if carga_str is not None else ""
    if not carga_str:
        return carga_str

    def repl(m: re.Match) -> str:
        n = float(m.group(0).replace(",", "."))
        if n == 0:
            return "0"
        reduzido = round(n * fator)
        return str(reduzido)

    return re.sub(r"\d+(?:[.,]\d+)?", repl, carga_str)


def main() -> None:
    if len(sys.argv) < 3:
        print("Uso: python scripts/seed_ponto_ficticio.py <codigo_cliente> <sessao>")
        sys.exit(1)
    cod_cliente = int(sys.argv[1])
    sessao_alvo = int(sys.argv[2])

    sheets = SheetsClient(
        credentials_file=os.environ["GOOGLE_CREDENTIALS_FILE"],
        sheet_id=os.environ["GOOGLE_SHEET_ID"],
    )

    rows = sheets.read_tab_all("HistoricoExecucoes")
    alvo = [
        r for r in rows
        if int(r.get("CodigoCliente") or 0) == cod_cliente
        and int(r.get("Sessao") or 0) == sessao_alvo
    ]
    if not alvo:
        print(f"Sem execuções pra cliente {cod_cliente} / sessão {sessao_alvo}")
        sys.exit(1)

    # Usa o timestamp mais antigo encontrado e recua 7 dias
    ts_original = min(r.get("TimestampExecucao") or "" for r in alvo)
    try:
        dt = datetime.fromisoformat(ts_original.replace("Z", "+00:00"))
    except ValueError:
        dt = datetime.now()
    dt_novo = dt - timedelta(days=7)
    novo_ts = dt_novo.isoformat().replace("+00:00", "Z")
    nova_data = dt_novo.strftime("%Y-%m-%d")

    # Agrupa apenas por par (Exercicio) — pega a 1ª ocorrência de cada
    ja_vistos: set[str] = set()
    fakes: list[dict] = []
    for r in alvo:
        ex = r.get("Exercicio") or ""
        if ex in ja_vistos:
            continue
        ja_vistos.add(ex)
        clone = dict(r)
        clone["DataCaptura"] = nova_data
        clone["TimestampExecucao"] = novo_ts
        clone["DataAlteracao"] = novo_ts
        clone["Carga"] = _reduzir_carga(clone.get("Carga") or "")
        clone["Observacoes"] = (clone.get("Observacoes") or "") + " [FICTICIO]"
        fakes.append(clone)

    nome = alvo[0].get("NomeCliente") or f"cliente {cod_cliente}"
    print(f"Criando ponto fictício pra {nome}, sessão {sessao_alvo}:")
    print(f"  Timestamp original: {ts_original}")
    print(f"  Timestamp fictício: {novo_ts}")
    print(f"  Exercícios duplicados: {len(fakes)}")
    for f in fakes:
        print(f"    · {f['Exercicio']}  {f['Carga']}")

    written = sheets.append_tab("HistoricoExecucoes", fakes)
    print(f"\n[ok] {written} linhas adicionadas em HistoricoExecucoes")


if __name__ == "__main__":
    main()
