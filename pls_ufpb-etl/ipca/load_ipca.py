"""IPCA mensal (BCB/SGS serie 433, variacao % no mes) -> colecao pls_ipca.

Guarda a variacao e um numero-indice encadeado (base: primeiro mes da
serie = 1.0). O deflator de um mes para o mes de referencia e
indice[ref] / indice[mes] -- calculado no modulo `indicadores`, porque o
mes de referencia muda a cada carga.

Sempre baixa a serie inteira desde IPCA_INICIO (sao ~150 pontos): o
indice encadeado so fica correto se todos os meses estiverem presentes.
"""

from __future__ import annotations

import os

import pandas as pd

from common import config
from common.http import HttpClient
from common.mongo import replace_by
from common.storage import raw_path, save_processed, write_json
from common.text import parse_valor
from common.validation import report_counts

COLLECTION = "pls_ipca"
IPCA_INICIO = os.environ.get("IPCA_INICIO", "01/01/2015")


def extract_transform() -> pd.DataFrame:
    client = HttpClient()
    dados = client.get_json(config.BCB_SGS_IPCA_URL, {"formato": "json", "dataInicial": IPCA_INICIO})
    write_json(raw_path("bcb", "ipca_sgs433.json"), dados)

    df = pd.DataFrame(dados)
    data = pd.to_datetime(df["data"], format="%d/%m/%Y")
    df = pd.DataFrame({
        "periodo": data.dt.strftime("%Y-%m"),
        "ano": data.dt.year,
        "mes": data.dt.month,
        "variacao_pct": df["valor"].map(parse_valor),
    }).sort_values("periodo").reset_index(drop=True)

    esperado = pd.period_range(df["periodo"].iloc[0], df["periodo"].iloc[-1], freq="M").strftime("%Y-%m")
    faltando = sorted(set(esperado) - set(df["periodo"]))
    if faltando:
        raise ValueError(f"Serie IPCA com meses faltando (indice encadeado ficaria errado): {faltando}")

    df["indice"] = (1 + df["variacao_pct"] / 100).cumprod()
    return df


def run(*, dry_run: bool = False, **_: object) -> None:
    df = extract_transform()
    ultimo = df.iloc[-1]
    report_counts("ipca", {"meses": len(df), f"ultimo mes ({ultimo['periodo']}) %": float(ultimo["variacao_pct"])})
    if not dry_run:
        save_processed(df, COLLECTION)
    replace_by(COLLECTION, df, "periodo", dry_run=dry_run)


if __name__ == "__main__":
    run()
