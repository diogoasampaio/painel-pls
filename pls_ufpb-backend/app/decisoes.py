"""Decisoes da Comissao do PLS por indicador (colecao pls_decisoes_comissao, de ref/decisoes_comissao.csv).

A coluna `indicadores` lista os codigos (Nxx do nucleo ou id do catalogo) separados por |.
"""

from __future__ import annotations

CAMPOS = ("id", "questao", "contexto", "opcoes", "efeito", "situacao", "decisao")


async def por_indicador(db) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    async for d in db["pls_decisoes_comissao"].find({}, {"_id": 0}).sort("id", 1):
        item = {k: (d.get(k) or None) for k in CAMPOS}
        for cod in str(d.get("indicadores") or "").split("|"):
            if cod:
                out.setdefault(cod, []).append(item)
    return out
