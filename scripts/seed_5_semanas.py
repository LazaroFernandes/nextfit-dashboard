"""Cria histórico de 5 semanas pra uma sessão — simulação realista de progressão.

A semana 5 é a execução real mais recente. As semanas 1-4 são fictícias,
com multiplicadores que formam curva realista (bump/plateau/deload).

Uso:
    python scripts/seed_5_semanas.py <codigo_cliente> <sessao>
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

# (offset_em_dias_a_partir_da_execucao_real, multiplicador_da_carga_real)
# Curva: 70% → 75% → 73% (deload) → 85% (já existe) → 100% (real)
# Se o offset já tiver fake registrado, o script pula (idempotente).
CURVA_SEMANAS = [
    (-28, 0.70),
    (-21, 0.75),
    (-14, 0.73),
    (-7, 0.85),
]


def _aplicar_fator(carga_str, fator: float) -> str:
    carga_str = str(carga_str) if carga_str is not None else ""
    if not carga_str:
        return carga_str

    def repl(m: re.Match) -> str:
        n = float(m.group(0).replace(",", "."))
        if n == 0:
            return "0"
        return str(round(n * fator))

    return re.sub(r"\d+(?:[.,]\d+)?", repl, carga_str)


def main() -> None:
    if len(sys.argv) < 3:
        print("Uso: python scripts/seed_5_semanas.py <codigo_cliente> <sessao>")
        sys.exit(1)
    cod_cliente = int(sys.argv[1])
    sessao_alvo = int(sys.argv[2])

    sheets = SheetsClient(
        credentials_file=os.environ["GOOGLE_CREDENTIALS_FILE"],
        sheet_id=os.environ["GOOGLE_SHEET_ID"],
    )

    rows = sheets.read_tab_all("HistoricoExecucoes")

    # Pega apenas execuções REAIS (sem marcador [FICTICIO] na observação)
    reais = [
        r for r in rows
        if int(r.get("CodigoCliente") or 0) == cod_cliente
        and int(r.get("Sessao") or 0) == sessao_alvo
        and "[FICTICIO]" not in str(r.get("Observacoes") or "")
    ]
    if not reais:
        print(f"Nenhuma execução real pra cliente {cod_cliente} / sessão {sessao_alvo}")
        sys.exit(1)

    # Usa o timestamp da execução real como âncora
    ts_real = max(r.get("TimestampExecucao") or "" for r in reais)
    dt_real = datetime.fromisoformat(ts_real.replace("Z", "+00:00"))

    # Datas já cobertas por fakes existentes (pra não duplicar)
    datas_fake_existentes = {
        str(r.get("DataCaptura"))
        for r in rows
        if int(r.get("CodigoCliente") or 0) == cod_cliente
        and int(r.get("Sessao") or 0) == sessao_alvo
        and "[FICTICIO]" in str(r.get("Observacoes") or "")
    }

    # Um exercício por linha (pega 1 entrada única por nome)
    vistos: set[str] = set()
    templates: list[dict] = []
    for r in reais:
        ex = r.get("Exercicio") or ""
        if ex in vistos:
            continue
        vistos.add(ex)
        templates.append(r)

    nome = templates[0].get("NomeCliente") or f"cliente {cod_cliente}"
    print(f"Gerando 4 pontos fictícios pra {nome}, sessão {sessao_alvo}")
    print(f"  Execução real (semana 5): {ts_real}")

    fakes: list[dict] = []
    for offset_dias, fator in CURVA_SEMANAS:
        dt_novo = dt_real + timedelta(days=offset_dias)
        novo_ts = dt_novo.isoformat().replace("+00:00", "Z")
        nova_data = dt_novo.strftime("%Y-%m-%d")
        if nova_data in datas_fake_existentes:
            print(f"  {nova_data} ({offset_dias}d): já tem fake — pulando")
            continue
        print(f"  {nova_data} ({offset_dias}d, fator {fator:.2f}):")
        for t in templates:
            clone = dict(t)
            clone["DataCaptura"] = nova_data
            clone["TimestampExecucao"] = novo_ts
            clone["DataAlteracao"] = novo_ts
            clone["Carga"] = _aplicar_fator(clone.get("Carga") or "", fator)
            obs = str(clone.get("Observacoes") or "")
            clone["Observacoes"] = (obs + " [FICTICIO]").strip()
            fakes.append(clone)
            print(f"    · {clone['Exercicio']}  {clone['Carga']}")

    written = sheets.append_tab("HistoricoExecucoes", fakes)
    print(f"\n[ok] {written} linhas adicionadas em HistoricoExecucoes")


if __name__ == "__main__":
    main()
