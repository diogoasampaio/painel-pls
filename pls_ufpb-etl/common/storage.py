"""Camadas raw e processed em disco.

raw/        resposta bruta de cada fonte, como chegou (auditoria e cache
            para retomar carga historica interrompida)
processed/  parquet por modulo, ja tratado -- e o que vai para o Mongo e o
            que o modulo `indicadores` le (dispensa Mongo para montar os
            agregados e serve direto ao Power BI, se preciso)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from . import config


def raw_path(*parts: str) -> Path:
    path = config.RAW_DIR.joinpath(*parts)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)  # escrita atomica: carga interrompida nao deixa cache corrompido


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def processed_path(name: str) -> Path:
    config.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    return config.PROCESSED_DIR / f"{name}.parquet"


def save_processed(df: pd.DataFrame, name: str, *, replace_on: str | None = None) -> Path:
    """Grava o parquet do modulo. Com `replace_on`, substitui so os valores
    dessa coluna presentes em `df` (mesma semantica do delete_many+insert do
    Mongo) e preserva o restante do historico ja processado.
    """
    path = processed_path(name)
    if replace_on and path.exists() and not df.empty:
        old = pd.read_parquet(path)
        if replace_on in old.columns:
            old = old[~old[replace_on].isin(df[replace_on].unique())]
            df = pd.concat([old, df], ignore_index=True)
    df.to_parquet(path, index=False)
    return path


def load_processed(name: str) -> pd.DataFrame:
    path = processed_path(name)
    return pd.read_parquet(path) if path.exists() else pd.DataFrame()
