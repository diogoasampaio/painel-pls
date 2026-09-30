"""Denominadores do PLS (comunidade academica) a partir do Censo da
Educacao Superior (INEP, microdados) -> colecao pls_comunidade.

Por ano do censo e por universidade federal (para benchmark entre IFES):
  docentes_exercicio   QT_DOC_EXE   (arquivo IES)
  tecnicos             QT_TEC_TOTAL (arquivo IES)
  matriculas           soma de QT_MAT dos cursos de graduacao (arquivo CURSOS)
  matriculas_presencial  idem, TP_MODALIDADE_ENSINO == 1
  comunidade           matriculas + docentes_exercicio + tecnicos

O zip tem ~450 MB e e lido por HTTP Range (common/remote_zip.py): o
arquivo IES (1 MB) sai barato; o de CURSOS (~450 MB, sem compressao) e
percorrido em streaming uma unica vez por ano. O resumo por IES fica em
data/raw/inep/<ano>.json e reprocessar o ano nao baixa de novo.

Pos-graduacao stricto sensu nao esta no Censo da Educacao Superior
(fonte: CAPES/Sucupira) e terceirizados nao estao em fonte publica
estruturada -- `comunidade` e portanto um piso.

Anos ainda nao publicados (o censo de N sai no fim de N+1) sao pulados.
"""

from __future__ import annotations

import pandas as pd
import requests

from common import config
from common.mongo import replace_by
from common.periodo import Janela
from common.remote_zip import open_remote_zip
from common.storage import raw_path, read_json, save_processed, write_json
from common.validation import report_counts

COLLECTION = "pls_comunidade"
CATEGORIA_FEDERAL = "1"
ORGANIZACAO_UNIVERSIDADE = "1"


def _membro(z, trecho: str) -> str:
    nomes = [n for n in z.namelist() if trecho in n.upper() and n.upper().endswith(".CSV")]
    if not nomes:
        raise FileNotFoundError(f"{trecho} nao encontrado no zip do INEP: {z.namelist()}")
    return nomes[0]


def _resumo_ano(ano: int) -> list[dict] | None:
    cache = raw_path("inep", f"{ano}.json")
    if cache.exists():
        return read_json(cache)

    url = config.INEP_MICRODADOS_URL.format(ano=ano)
    try:
        z = open_remote_zip(url)
    except requests.HTTPError as exc:
        if exc.response is not None and exc.response.status_code == 404:
            print(f"  INEP {ano}: microdados ainda nao publicados")
            return None
        raise

    with z.open(_membro(z, "_IES_")) as f:
        ies = pd.read_csv(f, sep=";", encoding="latin-1", dtype=str, low_memory=False)
    ies = ies[
        (ies["TP_CATEGORIA_ADMINISTRATIVA"] == CATEGORIA_FEDERAL)
        & (ies["TP_ORGANIZACAO_ACADEMICA"] == ORGANIZACAO_UNIVERSIDADE)
    ]
    federais = set(ies["CO_IES"])

    print(f"  INEP {ano}: lendo matriculas (arquivo de cursos, streaming ~450 MB)...", flush=True)
    partes = []
    with z.open(_membro(z, "CURSOS")) as f:
        for chunk in pd.read_csv(
            f, sep=";", encoding="latin-1", dtype=str, chunksize=200_000,
            usecols=["CO_IES", "TP_MODALIDADE_ENSINO", "QT_MAT"],
        ):
            chunk = chunk[chunk["CO_IES"].isin(federais)]
            chunk["QT_MAT"] = pd.to_numeric(chunk["QT_MAT"], errors="coerce").fillna(0)
            chunk["QT_MAT_PRES"] = chunk["QT_MAT"].where(chunk["TP_MODALIDADE_ENSINO"] == "1", 0)
            partes.append(chunk.groupby("CO_IES")[["QT_MAT", "QT_MAT_PRES"]].sum())
    mat = pd.concat(partes).groupby(level=0).sum() if partes else pd.DataFrame(columns=["QT_MAT", "QT_MAT_PRES"])

    registros = []
    for r in ies.itertuples():
        m = mat.loc[r.CO_IES] if r.CO_IES in mat.index else None
        docentes = int(float(r.QT_DOC_EXE or 0))
        tecnicos = int(float(r.QT_TEC_TOTAL or 0))
        matriculas = int(m["QT_MAT"]) if m is not None else 0
        registros.append({
            "ano": ano, "co_ies": r.CO_IES, "sg_ies": r.SG_IES, "no_ies": r.NO_IES, "uf": r.SG_UF_IES,
            "regiao": r.NO_REGIAO_IES, "docentes_exercicio": docentes, "tecnicos": tecnicos,
            "matriculas": matriculas,
            "matriculas_presencial": int(m["QT_MAT_PRES"]) if m is not None else 0,
            "comunidade": matriculas + docentes + tecnicos,
        })
    write_json(cache, registros)
    return registros


def extract_transform(janela: Janela) -> pd.DataFrame:
    registros: list[dict] = []
    for ano in janela.anos():
        resumo = _resumo_ano(ano)
        if resumo:
            registros.extend(resumo)
    df = pd.DataFrame(registros)
    if not df.empty:
        df["ufpb"] = df["co_ies"] == config.CO_IES_INEP
    return df


def run(*, dry_run: bool = False, inicio: str | None = None, fim: str | None = None, **_: object) -> None:
    # sem janela explicita: os ultimos 3 censos que podem ter saido
    if not inicio and not fim:
        from datetime import date

        ano = date.today().year
        inicio, fim = f"{ano - 3}-01", f"{ano - 1}-12"
    df = extract_transform(Janela.de_args(inicio, fim))
    if df.empty:
        print("INEP: nenhum ano disponivel na janela")
        return
    ufpb = df[df["ufpb"]].set_index("ano")
    report_counts("INEP - UFPB (comunidade por ano)", {str(a): int(v) for a, v in ufpb["comunidade"].items()})
    report_counts("INEP - universidades federais por ano", df.groupby("ano").size().rename(str).to_dict())
    if not dry_run:
        save_processed(df, COLLECTION, replace_on="ano")
    replace_by(COLLECTION, df, "ano", dry_run=dry_run)


if __name__ == "__main__":
    run()
