"""GET /pls/metas -- indicadores do PLS 2025-2029 por eixo, com meta, rota
de automacao e o valor de cada ano.

Le pls_catalogo_indicadores (ref/indicadores_pls.csv, via `referencias`)
e pls_metas (modulo `metas` do ETL). Indicador sem valor ainda aparece,
com `valores` vazio: o painel mostra o plano inteiro, nao so o que ja
tem dado.

    ?eixo=1..6          recorte por eixo
    ?plano=true         so os indicadores do plano (sem as ampliacoes A*)
"""

from __future__ import annotations

from fastapi import APIRouter, Query, Request

from app.db import get_database
from app.decisoes import por_indicador
from app.models.pls import MetasOut


def register_metas_routes(router: APIRouter) -> None:
    @router.get("/metas", response_model=MetasOut)
    async def metas(
        request: Request,
        eixo: str | None = Query(None, pattern=r"^[1-6]$"),
        plano: bool = False,
    ) -> dict:
        db = get_database(request)
        filtro: dict = {}
        if eixo:
            filtro["eixo_pls"] = eixo
        if plano:
            filtro["id"] = {"$regex": "^E"}

        valores: dict[str, list[dict]] = {}
        async for v in db["pls_metas"].find({k: v for k, v in filtro.items() if k == "eixo_pls"}, {"_id": 0}).sort("ano", 1):
            valores.setdefault(v["indicador_id"], []).append(v)

        decisoes = await por_indicador(db)
        indicadores = [
            {**c, "valores": valores.get(c["id"], []), "decisoes": decisoes.get(c["id"], [])}
            async for c in db["pls_catalogo_indicadores"].find(filtro, {"_id": 0}).sort("ordem", 1)  # ordem do CSV
        ]
        eixos = [e async for e in db["pls_eixos"].find({}, {"_id": 0}).sort("eixo_pls", 1)]
        return {"eixos": eixos, "indicadores": indicadores}
