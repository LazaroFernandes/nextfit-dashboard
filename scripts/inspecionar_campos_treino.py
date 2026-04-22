"""Descobre todos os campos que a API v2 retorna pra treino.

Objetivo: achar campos tipo ProximaSessao, UltimaExecucao, DataUltimaUtilizacao
que possam sinalizar quando o aluno finalizou uma sessão.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from dotenv import load_dotenv

from nextfit_v2_client import NextFitV2Client

ENV_PATH = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(ENV_PATH)


def main() -> None:
    v2 = NextFitV2Client(
        token=os.environ["NEXTFIT_V2_TOKEN"],
        codigo_unidade=int(os.environ["NEXTFIT_CODIGO_UNIDADE"]),
        refresh_token=os.environ.get("NEXTFIT_V2_REFRESH_TOKEN"),
        env_path=ENV_PATH,
    )

    # 1) Listagem — SEM filtro de fields, pra ver tudo que a API manda
    data = v2._get(
        "/api/v2/RelTreino/RecuperarRelTreino",
        {"limit": 3, "page": 1, "filter": "[]"},
    )
    content = data.get("Content") or []
    if not content:
        print("Sem treinos retornados")
        return

    print("=" * 70)
    print("LISTAGEM — campos em /api/v2/RelTreino/RecuperarRelTreino")
    print("=" * 70)
    for k, v in content[0].items():
        print(f"  {k}: {v!r}")

    # 2) Detalhe — RecuperarView
    treino_id = content[0]["Id"]
    print()
    print("=" * 70)
    print(f"DETALHE — /api/Treino/RecuperarView?Codigo={treino_id}")
    print("=" * 70)

    detalhe = v2.detalhe_treino(treino_id)
    for k, v in detalhe.items():
        if k == "Sessoes":
            print(f"  Sessoes: [{len(v)} sessão(ões)]")
            if v:
                print(f"    -- Campos da 1ª sessão:")
                for sk, sv in v[0].items():
                    if sk == "Exercicios":
                        print(f"      Exercicios: [{len(sv)}] — omitido")
                    else:
                        print(f"      {sk}: {sv!r}")
        else:
            print(f"  {k}: {v!r}")

    # 3) Dump bruto em JSON pra inspeção mais profunda
    out = Path("scripts/_dump_treino.json")
    out.write_text(
        json.dumps({"listagem": content, "detalhe": detalhe}, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    print(f"\nDump completo salvo em: {out}")


if __name__ == "__main__":
    main()
