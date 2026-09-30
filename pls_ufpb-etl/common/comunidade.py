"""Comunidade academica da UFPB: denominador dos indicadores por pessoa e em %
dos servidores.

Fonte preferida: a contagem institucional em ref/comunidade_ufpb.csv
(discentes, docentes, tecnicos-administrativos e terceirizados da UFPB por
ano). Ela cobre toda a comunidade, com pos-graduacao e terceirizados, e sai no
ano seguinte. O Censo INEP (pls_comunidade), com so graduacao, docentes em
exercicio e tecnicos, fica como reserva para ano que a planilha nao tiver.

Para atualizar o CSV a partir da planilha (colunas ANO, COMUNIDADE_ACADEMICA,
DISCENTES_UFPB, Docentes, TECNICOS_ADMINISTRATIVOS_UFPB, TERCEIRIZADOS_UFPB):

    python -m common.comunidade caminho/comunidade_academica.xlsx
"""

from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from common import config
from common.storage import load_processed

ARQUIVO = config.REF_DIR / "comunidade_ufpb.csv"
COLUNAS = ["ano", "discentes", "docentes", "tecnicos", "terceirizados", "comunidade"]
FONTE_UFPB = "UFPB"
FONTE_INEP = "Censo INEP"


def ufpb() -> pd.DataFrame:
    """Uma linha por ano (indice): comunidade, servidores (docentes + tecnicos) e fonte."""
    partes = []
    if ARQUIVO.exists():
        ref = pd.read_csv(ARQUIVO, sep=";")
        partes.append(ref.assign(servidores=ref["docentes"] + ref["tecnicos"], fonte=FONTE_UFPB)
                      [["ano", "comunidade", "servidores", "fonte"]])
    inep = load_processed("pls_comunidade")
    if not inep.empty:
        inep = inep[inep["ufpb"]]
        servidores = inep["docentes_exercicio"] + inep["tecnicos"] if "tecnicos" in inep else np.nan
        partes.append(pd.DataFrame({
            "ano": inep["ano"], "comunidade": inep["comunidade"], "servidores": servidores, "fonte": FONTE_INEP,
        }))
    if not partes:
        return pd.DataFrame(columns=["comunidade", "servidores", "fonte"], index=pd.Index([], name="ano"))
    # a planilha vem primeiro: o INEP so entra nos anos que ela nao tem
    df = pd.concat(partes).drop_duplicates("ano", keep="first")
    return df.astype({"ano": int}).set_index("ano").sort_index()


def por_ano(anos: pd.Series, campo: str) -> tuple[pd.Series, pd.Series]:
    """Valor de `campo` para cada ano (o do ano ou, sem ele, o ultimo anterior) e o ano usado."""
    tab = ufpb()
    if tab[campo].dropna().empty:
        return pd.Series(np.nan, index=anos.index), pd.Series(np.nan, index=anos.index)
    serie = tab[campo].dropna()

    def ano_ref(a: int) -> int:
        disponiveis = serie.index[serie.index <= a]
        return disponiveis.max() if len(disponiveis) else serie.index.min()

    ref = anos.map(ano_ref)
    return ref.map(serie), ref


def importar(xlsx: str) -> pd.DataFrame:
    bruto = pd.read_excel(xlsx)
    bruto.columns = [str(c).strip().upper() for c in bruto.columns]
    df = pd.DataFrame({
        "ano": bruto["ANO"], "discentes": bruto["DISCENTES_UFPB"], "docentes": bruto["DOCENTES"],
        "tecnicos": bruto["TECNICOS_ADMINISTRATIVOS_UFPB"], "terceirizados": bruto["TERCEIRIZADOS_UFPB"],
        "comunidade": bruto["COMUNIDADE_ACADEMICA"],
    }).dropna(subset=["ano"]).astype(int).sort_values("ano")
    soma = df[["discentes", "docentes", "tecnicos", "terceirizados"]].sum(axis=1)
    if (soma != df["comunidade"]).any():
        raise ValueError(f"comunidade diferente da soma das partes nos anos {df.loc[soma != df['comunidade'], 'ano'].tolist()}")
    df[COLUNAS].to_csv(ARQUIVO, sep=";", index=False)
    return df


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    print(importar(sys.argv[1]).to_string(index=False))
    print(f"-> {ARQUIVO}")
