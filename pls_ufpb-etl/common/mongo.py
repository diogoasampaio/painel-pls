from __future__ import annotations

import pandas as pd
from pymongo import MongoClient
from pymongo.database import Database

from . import config
from .records import to_mongo_records

_client: MongoClient | None = None


def get_db() -> Database:
    global _client
    if _client is None:
        if not config.MONGO_URI:
            raise RuntimeError("MONGO_URI nao configurada no .env (use --dry-run para rodar sem banco)")
        _client = MongoClient(config.MONGO_URI)
    return _client[config.MONGO_DB]


def replace_by(collection: str, df: pd.DataFrame, key: str, *, dry_run: bool = False) -> None:
    """delete_many({key: valores de df}) -> insert_many. Substitui o recorte
    inteiro (periodo, ano...) -- reprocessar um mes nunca duplica documento.
    """
    records = to_mongo_records(df)
    values = sorted(df[key].dropna().unique().tolist()) if not df.empty else []
    if dry_run:
        print(f"[dry-run] {len(records)} documentos seriam gravados em '{collection}' ({key}: {_resumo(values)})")
        return
    if config.SO_ARQUIVOS:
        print(f"[so-arquivos] {len(records)} documentos de '{collection}' so em data/processed ({key}: {_resumo(values)})")
        return
    db = get_db()
    db[collection].delete_many({key: {"$in": values}})
    if records:
        db[collection].insert_many(records)
    print(f"{len(records)} documentos gravados em '{collection}' ({key}: {_resumo(values)})")


def _resumo(values: list) -> str:
    if len(values) <= 4:
        return ", ".join(map(str, values)) or "-"
    return f"{values[0]} .. {values[-1]} ({len(values)} valores)"
