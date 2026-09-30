"""Catalogo de indicadores do PLS UFPB 2025-2029 (ref/indicadores_pls.csv).

Um indicador por linha: os 34 do plano (tabelas 16 a 24, ids E1..E6) e as
ampliacoes do painel (ids A1..A6, sem meta no plano).

  automacao  automatico  calculado pelo ETL a partir de dados publicos
             integracao  tem fonte estruturada (publica, do fornecedor ou
                         sistema interno) a integrar; ate la, lancado a mao
             informado   so existe em documento: lancado pela comissao
  tipo_fonte publica | fornecedor | interna | documental
  tipo_meta  reducao_vs_base  cair meta_valor % em relacao ao ano_base
             reducao_anual    cair meta_valor % em relacao ao ano anterior
             aumento_vs_base  subir meta_valor % em relacao ao ano_base
             aumento_anual    subir meta_valor % em relacao ao ano anterior
             minimo           valor >= meta_valor
             maximo           valor <= meta_valor
             booleano         1 = sim
             acompanhamento   sem meta (ampliacoes)
  calculo    como o ETL obtem o valor automatico:
             ind:metrica=..,tema=..,subtema=a|b,campo=..
                 soma anual da colecao pls_indicadores
             ...,razao_subtema=a|b|c
                 percentual: soma dos subtemas do filtro / soma dos
                 subtemas de razao_subtema (mesma metrica), x 100
             per_capita
                 valor lancado (total) / comunidade academica (common/comunidade.py)
"""

from __future__ import annotations

import pandas as pd

from common import pls_map

AUTOMACAO = {"automatico", "integracao", "informado"}
TIPO_FONTE = {"publica", "fornecedor", "interna", "documental"}
TIPO_META = {"reducao_vs_base", "reducao_anual", "aumento_vs_base", "aumento_anual", "minimo", "maximo", "booleano",
             "acompanhamento"}
VARIACAO = {"reducao_vs_base", "reducao_anual", "aumento_vs_base", "aumento_anual"}
CAMPOS = {"valor_nominal", "valor_real", "valor_real_per_capita", "valor_por_m2", "pct_servidores"}


def parse_calculo(spec: str) -> dict | None:
    spec = (spec or "").strip()
    if not spec:
        return None
    if spec == "per_capita":
        return {"tipo": "per_capita"}
    if not spec.startswith("ind:"):
        raise ValueError(f"calculo desconhecido: {spec!r}")
    params = dict(p.split("=", 1) for p in spec[4:].split(","))
    if "metrica" not in params or params.get("campo") not in CAMPOS:
        raise ValueError(f"calculo {spec!r}: precisa de metrica= e campo= ({', '.join(sorted(CAMPOS))})")
    return {
        "tipo": "ind",
        "metrica": params["metrica"],
        "tema": params.get("tema"),
        "subtemas": params["subtema"].split("|") if params.get("subtema") else None,
        "campo": params["campo"],
        "razao_subtemas": params["razao_subtema"].split("|") if params.get("razao_subtema") else None,
    }


def validar(df: pd.DataFrame) -> None:
    erros = []
    dup = df["id"][df["id"].duplicated()].tolist()
    if dup:
        erros.append(f"ids repetidos: {dup}")
    for col, validos in (("automacao", AUTOMACAO), ("tipo_fonte", TIPO_FONTE), ("tipo_meta", TIPO_META)):
        ruins = sorted(set(df[col]) - validos)
        if ruins:
            erros.append(f"{col} invalido: {ruins}")
    for r in df.itertuples():
        try:
            calc = parse_calculo(r.calculo)
        except ValueError as e:
            erros.append(f"{r.id}: {e}")
            continue
        if r.automacao == "automatico" and calc is None:
            erros.append(f"{r.id}: automatico sem calculo")
        if r.tipo_meta != "acompanhamento" and pd.isna(pd.to_numeric(r.meta_valor, errors="coerce")):
            erros.append(f"{r.id}: meta_valor ausente para tipo_meta {r.tipo_meta}")
        if r.tipo_meta.endswith("_vs_base") and not str(r.ano_base).isdigit():
            erros.append(f"{r.id}: reducao_vs_base sem ano_base")
    if erros:
        raise ValueError("indicadores_pls.csv: " + "; ".join(erros))


def tipar(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["meta_valor"] = pd.to_numeric(df["meta_valor"], errors="coerce")
    df["ano_base"] = pd.to_numeric(df["ano_base"], errors="coerce").astype("Int64")
    return df


def carregar() -> pd.DataFrame:
    df = pls_map._read_ref("indicadores_pls")
    validar(df)
    return tipar(df)
