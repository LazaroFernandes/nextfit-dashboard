"""Identifica os clientes com treino cujo plano não está ativo."""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from dotenv import load_dotenv

from nextfit_client import NextFitClient
from nextfit_v2_client import NextFitV2Client

ENV_PATH = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(ENV_PATH)


def main() -> None:
    nf = NextFitClient(
        api_key=os.environ["NEXTFIT_API_KEY"],
        base_url=os.environ["NEXTFIT_BASE_URL"],
        version=os.environ.get("NEXTFIT_API_VERSION", "1"),
    )
    v2 = NextFitV2Client(
        token=os.environ["NEXTFIT_V2_TOKEN"],
        codigo_unidade=int(os.environ["NEXTFIT_CODIGO_UNIDADE"]),
        refresh_token=os.environ.get("NEXTFIT_V2_REFRESH_TOKEN"),
        env_path=str(ENV_PATH),
    )

    contratos = nf.contratos_cliente()
    # Mapeia cliente -> lista de status de contratos
    status_por_cliente: dict[int, list[str]] = {}
    for c in contratos:
        cod = c.get("codigoCliente")
        status = c.get("status")
        if cod is None:
            continue
        status_por_cliente.setdefault(cod, []).append(status or "(sem status)")

    ativos = {cod for cod, sts in status_por_cliente.items() if "Ativo" in sts}
    print(f"Clientes ativos: {len(ativos)}")

    resumos = list(v2.listar_treinos())
    print(f"Treinos totais: {len(resumos)}")

    inativos = [t for t in resumos if t.get("CodigoCliente") not in ativos]
    print(f"Treinos de clientes NÃO ativos: {len(inativos)}")
    print()
    for t in inativos:
        cod = t.get("CodigoCliente")
        nome = t.get("NomeCliente")
        treino = t.get("DescricaoTreino") or t.get("Descricao")
        sts = status_por_cliente.get(cod, ["(sem contrato)"])
        print(f"- {nome} (código {cod})")
        print(f"    Treino: {treino}")
        print(f"    Status dos contratos: {sts}")


if __name__ == "__main__":
    main()
