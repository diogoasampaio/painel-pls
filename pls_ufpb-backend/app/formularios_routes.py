"""Formularios dos setores: acompanhamento das acoes do PLS e valores dos
indicadores informados.

    GET  /pls/formularios/acesso          o que o token pode preencher, com o ultimo envio
    POST /pls/formularios/acompanhamento  1 acao no ciclo semestral corrente
    POST /pls/formularios/valores         1 indicador em 1 ano

Autenticacao: cabecalho X-Token-Formulario. O token e criado pelo ETL
(`python -m formularios.formularios criar SETOR --responsavel REGEX`) e so o
hash SHA-256 fica em pls_form_acessos; ele libera as acoes e os indicadores
cujo `responsavel` casa com a expressao do acesso ("*" = Comissao, tudo).

Cada envio e so inserido (pls_form_acompanhamento / pls_form_valores), nunca
alterado: o usuario do Mongo da API tem permissao so de insert nessas duas
colecoes. O ETL (`run.py diario`) leva o envio mais recente para os CSVs e
recalcula metas e acoes -- o painel mostra no dia seguinte.
"""

from __future__ import annotations

import hashlib
import math
import re
from datetime import date, datetime
from typing import Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field, field_validator

from app.db import get_database

SITUACOES_ENTREGA = {"nao_iniciada", "em_andamento", "concluida", "suspensa", "cancelada"}
SITUACOES_CONTINUA = {"realizada_no_ciclo", "nao_realizada_no_ciclo", "suspensa", "cancelada"}
EXIGE_EVIDENCIA = {"concluida", "realizada_no_ciclo"}
EXIGE_JUSTIFICATIVA = {"nao_realizada_no_ciclo", "suspensa", "cancelada"}
AUTOMACAO_INFORMAVEL = {"informado", "integracao"}
PRIMEIRO_ANO = 2023

Texto = Field(default="", max_length=2000)


def ciclo_de(d: date) -> str:
    return f"{d.year}-S{1 if d.month <= 6 else 2}"


class AcompanhamentoIn(BaseModel):
    acao_id: str = Field(max_length=20)
    situacao: Literal["nao_iniciada", "em_andamento", "concluida", "realizada_no_ciclo", "nao_realizada_no_ciclo",
                      "suspensa", "cancelada"]
    percentual: float | None = Field(default=None, ge=0, le=100)
    evidencia: str = Texto
    justificativa: str = Texto
    facilitadores: str = Texto
    dificuldades: str = Texto
    ajuste_sugerido: str = Texto
    informado_por: str = Field(min_length=3, max_length=120)


class ValorIn(BaseModel):
    indicador_id: str = Field(max_length=30)
    ano: int
    valor: float
    fonte: str = Field(min_length=3, max_length=300)
    observacao: str = Texto
    informado_por: str = Field(min_length=3, max_length=120)

    @field_validator("valor")
    @classmethod
    def _finito(cls, v: float) -> float:
        if not math.isfinite(v):
            raise ValueError("valor precisa ser um numero")
        return v


class EnvioOut(BaseModel):
    ok: bool
    registrado_em: str
    ciclo: str | None = None


async def acesso_do_token(request: Request, x_token_formulario: str = Header(default="")) -> dict:
    if not x_token_formulario or len(x_token_formulario) > 200:
        raise HTTPException(401, "Informe o token de acesso do setor")
    h = hashlib.sha256(x_token_formulario.encode()).hexdigest()
    acesso = await get_database(request)["pls_form_acessos"].find_one({"hash": h, "ativo": True}, {"_id": 0, "hash": 0})
    if not acesso:
        raise HTTPException(401, "Token invalido ou revogado")
    return acesso


def _pode(acesso: dict, responsavel: str | None) -> bool:
    regra = acesso.get("responsavel") or ""
    if regra == "*":
        return True
    return bool(regra) and re.search(regra, responsavel or "", re.IGNORECASE) is not None


def _agora() -> str:
    return datetime.now().isoformat(timespec="seconds")


def register_formularios_routes(router: APIRouter) -> None:
    @router.get("/formularios/acesso")
    async def acesso(request: Request, acesso: dict = Depends(acesso_do_token)) -> dict:
        db = get_database(request)
        ciclo = ciclo_de(date.today())
        ultimos: dict[str, dict] = {}
        async for e in db["pls_form_acompanhamento"].find({"ciclo": ciclo}, {"_id": 0}).sort("registrado_em", 1):
            ultimos[e["acao_id"]] = e
        acoes = [
            {**{k: a.get(k) for k in ("id", "acao", "tipo", "responsavel", "inicio", "fim", "meta", "eixo_pls",
                                       "situacao", "situacao_informada", "evidencia")},
             "envio_ciclo": ultimos.get(a["id"])}
            async for a in db["pls_acoes"].find({}, {"_id": 0}).sort("id", 1)
            if _pode(acesso, a.get("responsavel"))
        ]
        valores: dict[str, list[dict]] = {}
        async for v in db["pls_form_valores"].find({}, {"_id": 0}).sort("registrado_em", 1):
            valores.setdefault(v["indicador_id"], []).append(v)
        indicadores = [
            {**{k: c.get(k) for k in ("id", "indicador", "formula", "unidade", "meta", "responsavel", "automacao",
                                       "eixo_pls", "calculo")},
             "envios": valores.get(c["id"], [])[-5:]}
            async for c in db["pls_catalogo_indicadores"].find(
                {"automacao": {"$in": sorted(AUTOMACAO_INFORMAVEL)}}, {"_id": 0}).sort("ordem", 1)
            if _pode(acesso, c.get("responsavel"))
        ]
        return {"setor": acesso["setor"], "ciclo": ciclo, "ano_atual": date.today().year,
                "primeiro_ano": PRIMEIRO_ANO, "acoes": acoes, "indicadores": indicadores}

    @router.post("/formularios/acompanhamento", response_model=EnvioOut)
    async def acompanhamento(corpo: AcompanhamentoIn, request: Request, acesso: dict = Depends(acesso_do_token)) -> dict:
        db = get_database(request)
        acao = await db["pls_acoes"].find_one({"id": corpo.acao_id}, {"_id": 0, "tipo": 1, "responsavel": 1})
        if not acao or not _pode(acesso, acao.get("responsavel")):
            raise HTTPException(403, "Acao fora do escopo deste token")
        validas = SITUACOES_CONTINUA if acao.get("tipo") == "continua" else SITUACOES_ENTREGA
        if corpo.situacao not in validas:
            raise HTTPException(422, f"Situacao invalida para acao do tipo {acao.get('tipo')}: use {', '.join(sorted(validas))}")
        if corpo.situacao in EXIGE_EVIDENCIA and not corpo.evidencia.strip():
            raise HTTPException(422, "Informe a evidencia (link, numero de processo SIPAC ou documento)")
        if corpo.situacao in EXIGE_JUSTIFICATIVA and not corpo.justificativa.strip():
            raise HTTPException(422, "Informe a justificativa")
        doc = {**corpo.model_dump(), "ciclo": ciclo_de(date.today()), "setor": acesso["setor"], "registrado_em": _agora()}
        await db["pls_form_acompanhamento"].insert_one(doc)
        return {"ok": True, "registrado_em": doc["registrado_em"], "ciclo": doc["ciclo"]}

    @router.post("/formularios/valores", response_model=EnvioOut)
    async def valores(corpo: ValorIn, request: Request, acesso: dict = Depends(acesso_do_token)) -> dict:
        db = get_database(request)
        ind = await db["pls_catalogo_indicadores"].find_one({"id": corpo.indicador_id}, {"_id": 0, "responsavel": 1, "automacao": 1})
        if not ind or ind.get("automacao") not in AUTOMACAO_INFORMAVEL or not _pode(acesso, ind.get("responsavel")):
            raise HTTPException(403, "Indicador fora do escopo deste token")
        if not PRIMEIRO_ANO <= corpo.ano <= date.today().year:
            raise HTTPException(422, f"Ano deve estar entre {PRIMEIRO_ANO} e {date.today().year}")
        doc = {**corpo.model_dump(), "setor": acesso["setor"], "registrado_em": _agora()}
        await db["pls_form_valores"].insert_one(doc)
        return {"ok": True, "registrado_em": doc["registrado_em"]}
