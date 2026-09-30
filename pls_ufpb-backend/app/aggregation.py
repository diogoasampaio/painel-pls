"""Agregacoes MongoDB sobre `pls_indicadores` (separadas das rotas).

Os valores ja chegam deflacionados e divididos pela comunidade academica
(ETL, modulo indicadores) e sao aditivos entre subtemas -- aqui so ha
$match + $group + $sum, sem recalculo.
"""

from __future__ import annotations

from motor.motor_asyncio import AsyncIOMotorCollection


def build_match(
    *,
    temas: list[str] | None = None,
    metricas: list[str] | None = None,
    ano_inicio: int | None = None,
    ano_fim: int | None = None,
    subtema: str | None = None,
) -> dict:
    match: dict = {}
    if temas:
        match["tema_codigo"] = {"$in": temas}
    if metricas:
        match["metrica"] = {"$in": metricas}
    if ano_inicio or ano_fim:
        match["ano"] = {k: v for k, v in (("$gte", ano_inicio), ("$lte", ano_fim)) if v}
    if subtema:
        match["subtema"] = subtema
    return match


async def serie(
    col: AsyncIOMotorCollection, match: dict, *, campo: str, granularidade: str, por: str | None = None
) -> list[dict]:
    """Serie temporal por metrica (e opcionalmente por tema/subtema)."""
    tempo = "$ano" if granularidade == "ano" else "$periodo"
    chave = {"t": tempo, "metrica": "$metrica"}
    if por:
        chave["grupo"] = f"${por}"
    pipeline = [
        {"$match": match},
        {"$group": {"_id": chave, "valor": {"$sum": f"${campo}"}, "unidade": {"$first": "$unidade"}}},
        {"$sort": {"_id.t": 1}},
    ]
    out = []
    async for d in col.aggregate(pipeline):
        out.append({
            "periodo": str(d["_id"]["t"]),
            "metrica": d["_id"]["metrica"],
            "grupo": d["_id"].get("grupo"),
            "valor": round(d["valor"], 2) if d["valor"] is not None else None,
            "unidade": d.get("unidade"),
        })
    return out


async def total_por_ano(col: AsyncIOMotorCollection, match: dict, *, campo: str, por: str) -> list[dict]:
    pipeline = [
        {"$match": match},
        {"$group": {"_id": {"ano": "$ano", "grupo": f"${por}"}, "valor": {"$sum": f"${campo}"}}},
        {"$sort": {"_id.ano": 1}},
    ]
    return [
        {"ano": d["_id"]["ano"], "grupo": d["_id"]["grupo"], "valor": round(d["valor"] or 0, 2)}
        async for d in col.aggregate(pipeline)
    ]


def comparar_anos(totais: list[dict]) -> list[dict]:
    """Cards de destaque: ultimo ano do grupo vs o ano imediatamente anterior.

    Sem pagamento no ano anterior, o card fica sem variacao (valor_anterior None)
    em vez de pular para um ano mais antigo ("vs 2023" num card de 2025). Se o
    ano anterior e anterior a toda a serie carregada, ano_anterior tambem e None.
    """
    por_grupo: dict[str, dict[int, float]] = {}
    for t in totais:
        por_grupo.setdefault(t["grupo"], {})[t["ano"]] = t["valor"]
    primeiro = min((t["ano"] for t in totais), default=None)
    cards = []
    for grupo, anos in por_grupo.items():
        atual = max(anos)
        anterior = atual - 1 if primeiro is not None and atual - 1 >= primeiro else None
        base = anos.get(anterior) if anterior else None
        cards.append({
            "grupo": grupo,
            "ano": atual,
            "valor": anos[atual],
            "ano_anterior": anterior,
            "valor_anterior": base,
            "variacao_pct": round((anos[atual] / base - 1) * 100, 1) if base else None,
        })
    return cards
