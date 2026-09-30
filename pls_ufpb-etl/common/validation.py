"""Validacao de totais de carga.

Informativa, nao um assert: imprime a comparacao e deixa a decisao de
seguir para quem roda o ETL (mesmo padrao do prpg_avaliacao). Em modo
automatico (timer) as divergencias ficam no log do journald.

Para os modulos de API nao existe um EXPECTED_TOTALS fixo -- a referencia
vem da exportacao do Tesouro Gerencial (ver README, secao Validacao),
lida por `load_expected_csv`.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

import pandas as pd


def report_counts(
    label: str,
    actual: Mapping[str, float],
    expected: Mapping[str, float] | None = None,
    *,
    tolerance: float = 0.005,
) -> None:
    print(f"\n=== Totais de carga - {label} ===")
    keys = list(actual.keys())
    if expected:
        keys = list(dict.fromkeys([*expected.keys(), *actual.keys()]))
    for key in sorted(keys):
        got = actual.get(key, 0)
        exp = expected.get(key) if expected else None
        if exp is None:
            print(f"  {key}: {_fmt(got)} (sem referencia cadastrada)")
        elif exp == got or (exp and abs(got - exp) / abs(exp) <= tolerance):
            print(f"  {key}: {_fmt(got)} (OK, referencia {_fmt(exp)})")
        else:
            print(f"  {key}: {_fmt(got)} (referencia era {_fmt(exp)} - divergencia de {_fmt(got - exp, sign=True)}, confirme antes de seguir)")


def load_expected_csv(path: Path, key_cols: list[str], value_col: str, *, lower_cols: bool = False) -> dict[str, float] | None:
    """CSV de referencia (ex.: exportacao do Tesouro Gerencial) -> {chave: valor}."""
    if not path.exists():
        return None
    df = pd.read_csv(path, dtype=str, sep=None, engine="python")
    if lower_cols:
        df.columns = df.columns.str.strip().str.lower()
    if "natureza" in df:
        # aceita 3.3.90.39.43 ou 33903943
        df["natureza"] = df["natureza"].str.replace(r"\D", "", regex=True)
    from .text import parse_valor

    df[value_col] = df[value_col].map(parse_valor)
    grouped = df.groupby(key_cols)[value_col].sum()
    return {"|".join(map(str, k if isinstance(k, tuple) else (k,))): float(v) for k, v in grouped.items()}


def _fmt(v: float, sign: bool = False) -> str:
    if float(v).is_integer() and abs(v) < 1e6 and not sign:
        return f"{int(v)}"
    return f"{v:+,.2f}" if sign else f"{v:,.2f}"
