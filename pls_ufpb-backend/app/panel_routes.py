"""Registra as rotas do modulo a partir de app/panels.py.

GET /pls/paineis                 lista de paineis (slug, rotulo)
GET /pls/filtros                 anos, temas (com rotulos) e metricas disponiveis
GET /pls/{slug}                  series + cards de destaque do painel
    ?granularidade=ano|mes       (padrao ano)
    ?valor=nominal|real|per_capita|por_m2  (padrao real: R$ do ultimo mes com IPCA)
    ?ano_inicio= &ano_fim=       recorte de anos
    ?por=tema_codigo|subtema     quebra das series (padrao: subtema nos
                                 paineis tematicos, tema na visao geral)
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException, Query, Request

from app.aggregation import build_match, comparar_anos, serie, total_por_ano
from app.db import get_database
from app.models.pls import FiltrosOut, PainelOut, PainelResumo
from app.panels import VALOR_CAMPOS, PanelDef, find_panel

COLLECTION = "pls_indicadores"


def register_panel_routes(router: APIRouter, *, panels: list[PanelDef]) -> None:
    @router.get("/paineis", response_model=list[PainelResumo])
    async def listar_paineis() -> list[dict]:
        return [{"slug": p.slug, "label": p.label} for p in panels]

    @router.get("/filtros", response_model=FiltrosOut)
    async def listar_filtros(request: Request) -> dict:
        db = get_database(request)
        anos = await db[COLLECTION].distinct("ano")
        metricas = await db[COLLECTION].distinct("metrica")
        temas = [
            {"codigo": t["tema_codigo"], "label": t["tema"], "eixo": t.get("eixo_pls")}
            async for t in db["pls_temas"].find({}, {"_id": 0}).sort("ordem", 1)
        ]
        return {"anos": sorted(int(a) for a in anos), "temas": temas, "metricas": sorted(metricas)}

    @router.get("/{slug}", response_model=PainelOut)
    async def painel(
        request: Request,
        slug: str,
        granularidade: Literal["ano", "mes"] = "ano",
        valor: Literal["nominal", "real", "per_capita", "por_m2"] = "real",
        ano_inicio: int | None = Query(None, ge=2000, le=2100),
        ano_fim: int | None = Query(None, ge=2000, le=2100),
        por: Literal["tema_codigo", "subtema"] | None = None,
    ) -> dict:
        p = find_panel(slug)
        if p is None:
            raise HTTPException(404, f"painel '{slug}' nao existe")
        col = get_database(request)[COLLECTION]
        campo = VALOR_CAMPOS[valor]
        quebra = por or ("subtema" if p.temas else "tema_codigo")
        match = build_match(temas=p.temas, metricas=list(p.metricas), ano_inicio=ano_inicio, ano_fim=ano_fim)

        series = await serie(col, match, campo=campo, granularidade=granularidade, por=quebra)
        # R$ tem unidade "R$"; metricas fisicas ignoram deflator/per capita
        # no ETL, entao o mesmo campo serve para todas.
        destaque_match = {**match, "metrica": p.destaque}
        # cards comparam anos completos: ano corrente pela metade daria
        # "queda" falsa contra o ano anterior inteiro
        ultimo = await col.find_one(destaque_match, {"periodo": 1}, sort=[("periodo", -1)])
        if ultimo and not ultimo["periodo"].endswith("-12"):
            destaque_match["ano"] = {**destaque_match.get("ano", {}), "$lt": int(ultimo["periodo"][:4])}
        cards = comparar_anos(await total_por_ano(col, destaque_match, campo=campo, por=quebra))
        return {
            "slug": p.slug,
            "label": p.label,
            "metricas": [{"codigo": k, "label": v} for k, v in p.metricas.items()],
            "valor": valor,
            "granularidade": granularidade,
            "por": quebra,
            "series": series,
            "destaques": cards,
        }
