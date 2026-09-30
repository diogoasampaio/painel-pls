"""GET /pls/execucao -- indice sintetico de execucao do PLS e faixas dos indicadores.

Le pls_execucao (modulo `execucao` do ETL):

    ?conjunto=plano|nucleo   plano = 34 indicadores do PLS; nucleo = conjunto minimo
    ?ano=AAAA                ano do detalhe (eixos e indicadores); padrao = o ano de onde vem o
                             alcance das metas do indice mais recente (no ano em curso as metas
                             ainda nao sao avaliaveis, entao o detalhe mostra o ultimo avaliado)

Devolve a serie anual do indice (geral), o recorte por eixo e a faixa de
cada indicador no ano (com `historico`: a serie anual do nucleo desde o 1o ano
com dado, e `projecao`: meta projetada e projecao do ano corrente, proposta a
validar pela Comissao), mais a definicao das faixas e os pesos usados.
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Query, Request

from app.db import get_database
from app.decisoes import por_indicador

CAMPOS_GERAL = ("ano", "indice_sintetico", "indice_metas", "indice_metas_usado", "ano_metas", "indice_acoes",
                "componentes", "n_indicadores", "n_com_meta", "n_avaliados", "cobertura_pct", "ano_fechado")


CAMPOS_PROJECAO = ("ano", "valor_parcial", "meses", "projecao", "metodo", "meta_projetada", "faixa_min", "faixa_max",
                   "regra", "parametro", "ano_base", "sentido", "fundamento", "situacao_projecao", "alcance_projecao")


def _faixas_contagem(doc: dict, codigos: list[str]) -> dict[str, int]:
    return {c: int(doc.get(f"faixa_{c}") or 0) for c in codigos}


def _limpo(v):
    # NaN do pandas chega como float nan
    return None if isinstance(v, float) and v != v else v


def register_execucao_routes(router: APIRouter) -> None:
    @router.get("/execucao")
    async def execucao(
        request: Request,
        conjunto: Literal["plano", "nucleo"] = "nucleo",
        ano: int | None = Query(None, ge=2000, le=2100),
    ) -> dict:
        col = get_database(request)["pls_execucao"]
        docs = [d async for d in col.find({"conjunto": conjunto}, {"_id": 0})]
        faixas = sorted((d for d in docs if d["nivel"] == "faixa"), key=lambda d: d["ordem"])
        codigos = [f["codigo"] for f in faixas]
        geral = sorted((d for d in docs if d["nivel"] == "geral"), key=lambda d: d["ano"])
        if not geral:
            return {"conjunto": conjunto, "ano": None, "ano_detalhe": None, "serie": [], "eixos": [], "indicadores": [], "faixas": [],
                    "parametros": {}}
        anos = [g["ano"] for g in geral]
        atual = geral[-1]["ano"]
        if ano not in anos:
            ano_metas = _limpo(geral[-1].get("ano_metas"))
            ano = int(ano_metas) if ano_metas in anos else atual
        serie = [{**{k: _limpo(g.get(k)) for k in CAMPOS_GERAL}, "faixas": _faixas_contagem(g, codigos)} for g in geral]
        eixos = sorted(
            ({"eixo_pls": d["eixo_pls"], "indice_metas": _limpo(d.get("indice_metas")), "n_com_meta": d.get("n_com_meta"),
              "n_avaliados": d.get("n_avaliados"), "cobertura_pct": _limpo(d.get("cobertura_pct")),
              "faixas": _faixas_contagem(d, codigos)}
             for d in docs if d["nivel"] == "eixo" and d["ano"] == ano),
            key=lambda d: d["eixo_pls"])
        nomes_eixo = {e["eixo_pls"]: e["eixo"] async for e in get_database(request)["pls_eixos"].find({}, {"_id": 0})}
        for e in eixos:
            e["eixo"] = nomes_eixo.get(e["eixo_pls"])
        # valor mais recente de cada indicador (o ano do detalhe pode nao ter valor ainda, ex.: N15 so no ano corrente)
        ultimo_valor: dict[str, dict] = {}
        for d in sorted((d for d in docs if d["nivel"] == "indicador" and _limpo(d.get("valor")) is not None),
                        key=lambda d: d["ano"]):
            ultimo_valor[d["codigo"]] = {"ano": d["ano"], "valor": d["valor"], "ano_completo": _limpo(d.get("ano_completo"))}
        indicadores = sorted(
            ({k: _limpo(d.get(k)) for k in ("codigo", "indicador_id", "indicador", "eixo_pls", "tipo_meta", "alcance_pct",
                                               "faixa", "situacao", "valor", "ano_completo", "unidade", "meta",
                                               "meta_sugerida", "formula", "automacao", "fonte", "polaridade",
                                               "o_que_mede", "periodicidade", "responsavel", "grupo", "no_indice")}
             for d in docs if d["nivel"] == "indicador" and d["ano"] == ano),
            key=lambda d: d["codigo"])
        # serie anual de cada indicador do nucleo (nivel "historico" do ETL, desde o 1o ano com dado)
        historico: dict[str, list[dict]] = {}
        for d in sorted((d for d in docs if d["nivel"] == "historico"), key=lambda d: d["ano"]):
            historico.setdefault(d["codigo"], []).append(
                {"ano": d["ano"], "valor": _limpo(d.get("valor")), "ano_completo": _limpo(d.get("ano_completo"))})
        # meta projetada e projecao do ano corrente (nivel "projecao" do ETL; proposta a validar)
        projecao = {d["codigo"]: {k: _limpo(d.get(k)) for k in CAMPOS_PROJECAO}
                    for d in docs if d["nivel"] == "projecao"}
        decisoes = await por_indicador(get_database(request))
        for i in indicadores:
            # decisoes da Comissao citadas pelo codigo do nucleo ou pelo id do catalogo, sem repetir
            vistas = {d["id"]: d for cod in (i["codigo"], i.get("indicador_id")) if cod for d in decisoes.get(cod, [])}
            i["decisoes"] = list(vistas.values())
            i["ultimo"] = ultimo_valor.get(i["codigo"])
            i["historico"] = historico.get(i["codigo"], [])
            i["projecao"] = projecao.get(i["codigo"])
        par = next((d for d in docs if d["nivel"] == "parametros"), {})
        return {
            "conjunto": conjunto, "ano": atual, "ano_detalhe": ano, "serie": serie, "eixos": eixos, "indicadores": indicadores,
            "faixas": [{k: _limpo(f.get(k)) for k in ("codigo", "faixa", "alcance_minimo", "descricao")} for f in faixas],
            "parametros": {k: _limpo(par.get(k)) for k in ("peso_metas", "peso_acoes", "agregacao_metas", "primeiro_ano")},
        }
