"""GET /pls/saude -- o que a ultima carga do ETL deixou pendente.

Le pls_saude_carga (modulo `saude` do ETL, roda no fim da carga mensal):
a ultima execucao inteira e o resumo das 12 anteriores.
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel

from app.db import get_database


class ItemSaudeOut(BaseModel):
    verificacao: str
    modulo: str
    nivel: str
    titulo: str
    quantidade: int
    detalhe: list[str]
    acao_sugerida: str


class ExecucaoResumoOut(BaseModel):
    execucao: str
    erro: int
    atencao: int


class SaudeOut(BaseModel):
    execucao: str | None
    itens: list[ItemSaudeOut]
    historico: list[ExecucaoResumoOut]


def register_saude_routes(router: APIRouter) -> None:
    @router.get("/saude", response_model=SaudeOut)
    async def saude(request: Request) -> dict:
        col = get_database(request)["pls_saude_carga"]
        historico = [
            {"execucao": h["_id"], "erro": h["erro"], "atencao": h["atencao"]}
            async for h in col.aggregate([
                {"$group": {
                    "_id": "$execucao",
                    "erro": {"$sum": {"$cond": [{"$eq": ["$nivel", "erro"]}, 1, 0]}},
                    "atencao": {"$sum": {"$cond": [{"$eq": ["$nivel", "atencao"]}, 1, 0]}},
                }},
                {"$sort": {"_id": -1}},
                {"$limit": 12},
            ])
        ]
        if not historico:
            return {"execucao": None, "itens": [], "historico": []}
        ultima = historico[0]["execucao"]
        ordem = {"erro": 0, "atencao": 1, "info": 2, "ok": 3}
        itens = [d async for d in col.find({"execucao": ultima}, {"_id": 0})]
        itens.sort(key=lambda d: (ordem.get(d["nivel"], 9), d["modulo"]))
        return {"execucao": ultima, "itens": itens, "historico": historico}
