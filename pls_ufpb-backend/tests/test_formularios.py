"""Formularios (token por setor, escopo pelo responsavel) e saude da carga."""

import asyncio
import hashlib

import pytest
from fastapi.testclient import TestClient
from mongomock_motor import AsyncMongoMockClient

SINFRA = "token-sinfra-123"
COMISSAO = "token-comissao-456"
REVOGADO = "token-antigo-789"


def _h(t):
    return hashlib.sha256(t.encode()).hexdigest()


@pytest.fixture
def ctx(monkeypatch):
    import app.db

    mock = AsyncMongoMockClient()
    monkeypatch.setattr(app.db, "AsyncIOMotorClient", lambda *_a, **_k: mock)
    from app.main import app as fastapi_app

    db = mock["painel_pls"]

    async def seed():
        await db.pls_form_acessos.insert_many([
            {"setor": "SINFRA", "hash": _h(SINFRA), "responsavel": "SINFRA", "ativo": True},
            {"setor": "Comissão", "hash": _h(COMISSAO), "responsavel": "*", "ativo": True},
            {"setor": "Antigo", "hash": _h(REVOGADO), "responsavel": "*", "ativo": False},
        ])
        await db.pls_acoes.insert_many([
            {"id": "T16-01", "acao": "Diagnóstico hidráulico", "tipo": "entrega", "responsavel": "SINFRA", "fim": "2026-09"},
            {"id": "T24-01", "acao": "Campanha", "tipo": "continua", "responsavel": "Ascom", "fim": "2029-12"},
        ])
        await db.pls_catalogo_indicadores.insert_many([
            {"id": "E1-ENERGIA-02", "indicador": "Geração solar", "responsavel": "SINFRA", "automacao": "informado", "ordem": 1},
            {"id": "E6-CAMPANHA-01", "indicador": "Campanhas", "responsavel": "Ascom", "automacao": "informado", "ordem": 2},
            {"id": "A1-GEE-01", "indicador": "GEE", "responsavel": "SINFRA", "automacao": "automatico", "ordem": 3},
        ])
        await db.pls_saude_carga.insert_many([
            {"execucao": "2026-08-10T01:00:00", "verificacao": "x", "modulo": "faturas", "nivel": "erro", "titulo": "velho",
             "quantidade": 0, "detalhe": [], "acao_sugerida": ""},
            {"execucao": "2026-09-10T01:00:00", "verificacao": "a", "modulo": "evg", "nivel": "ok", "titulo": "EVG em dia",
             "quantidade": 0, "detalhe": [], "acao_sugerida": ""},
            {"execucao": "2026-09-10T01:00:00", "verificacao": "b", "modulo": "faturas", "nivel": "atencao",
             "titulo": "2 processos sem leitura", "quantidade": 2, "detalhe": ["p1", "p2"], "acao_sugerida": "abrir no SIPAC"},
        ])

    asyncio.run(seed())
    fastapi_app.state.limiter.reset()
    with TestClient(fastapi_app) as c:
        yield c, db


def _acomp(**kw):
    return {"acao_id": "T16-01", "situacao": "em_andamento", "percentual": 40, "informado_por": "Fulana (SINFRA)", **kw}


def test_sem_token_ou_revogado_401(ctx):
    c, _ = ctx
    assert c.get("/pls/formularios/acesso").status_code == 401
    assert c.get("/pls/formularios/acesso", headers={"X-Token-Formulario": "errado"}).status_code == 401
    assert c.get("/pls/formularios/acesso", headers={"X-Token-Formulario": REVOGADO}).status_code == 401


def test_escopo_pelo_responsavel(ctx):
    c, _ = ctx
    r = c.get("/pls/formularios/acesso", headers={"X-Token-Formulario": SINFRA}).json()
    assert r["setor"] == "SINFRA"
    assert [a["id"] for a in r["acoes"]] == ["T16-01"]
    assert [i["id"] for i in r["indicadores"]] == ["E1-ENERGIA-02"]  # automatico nao entra
    tudo = c.get("/pls/formularios/acesso", headers={"X-Token-Formulario": COMISSAO}).json()
    assert len(tudo["acoes"]) == 2 and len(tudo["indicadores"]) == 2


def test_envio_de_acompanhamento_grava_com_setor_e_ciclo(ctx):
    c, db = ctx
    r = c.post("/pls/formularios/acompanhamento", json=_acomp(), headers={"X-Token-Formulario": SINFRA})
    assert r.status_code == 200 and r.json()["ciclo"].count("-S") == 1
    doc = asyncio.run(db.pls_form_acompanhamento.find_one({}))
    assert doc["setor"] == "SINFRA" and doc["percentual"] == 40
    ultimo = c.get("/pls/formularios/acesso", headers={"X-Token-Formulario": SINFRA}).json()["acoes"][0]["envio_ciclo"]
    assert ultimo["situacao"] == "em_andamento"


def test_regras_do_acompanhamento(ctx):
    c, _ = ctx
    h = {"X-Token-Formulario": SINFRA}
    assert c.post("/pls/formularios/acompanhamento", json=_acomp(acao_id="T24-01"), headers=h).status_code == 403
    assert c.post("/pls/formularios/acompanhamento", json=_acomp(situacao="concluida"), headers=h).status_code == 422
    assert c.post("/pls/formularios/acompanhamento", json=_acomp(situacao="realizada_no_ciclo", evidencia="x"),
                  headers=h).status_code == 422  # tipo entrega nao aceita situacao de acao continua
    assert c.post("/pls/formularios/acompanhamento", json=_acomp(situacao="cancelada"), headers=h).status_code == 422
    assert c.post("/pls/formularios/acompanhamento", json=_acomp(percentual=120), headers=h).status_code == 422
    assert c.post("/pls/formularios/acompanhamento", json=_acomp(situacao="concluida", evidencia="SIPAC 23074.1/2026"),
                  headers=h).status_code == 200


def test_valor_informado(ctx):
    c, db = ctx
    h = {"X-Token-Formulario": SINFRA}
    base = {"indicador_id": "E1-ENERGIA-02", "ano": 2025, "valor": 812345.5, "fonte": "Monitoramento dos inversores",
            "informado_por": "Fulano (SINFRA)"}
    assert c.post("/pls/formularios/valores", json=base, headers=h).status_code == 200
    assert c.post("/pls/formularios/valores", json={**base, "indicador_id": "A1-GEE-01"}, headers=h).status_code == 403
    assert c.post("/pls/formularios/valores", json={**base, "indicador_id": "E6-CAMPANHA-01"}, headers=h).status_code == 403
    assert c.post("/pls/formularios/valores", json={**base, "ano": 2019}, headers=h).status_code == 422
    assert asyncio.run(db.pls_form_valores.count_documents({})) == 1


def test_saude_mostra_ultima_execucao(ctx):
    c, _ = ctx
    r = c.get("/pls/saude").json()
    assert r["execucao"] == "2026-09-10T01:00:00"
    assert [i["nivel"] for i in r["itens"]] == ["atencao", "ok"]
    assert r["historico"] == [{"execucao": "2026-09-10T01:00:00", "erro": 0, "atencao": 1},
                              {"execucao": "2026-08-10T01:00:00", "erro": 1, "atencao": 0}]


def test_execucao_indice_e_faixas(ctx):
    c, db = ctx
    geral = {"conjunto": "nucleo", "nivel": "geral", "n_indicadores": 3, "n_com_meta": 2, "componentes": "metas+acoes",
             "faixa_atingida": 1, "faixa_distante": 1, "faixa_sem_meta": 1}
    asyncio.run(db.pls_execucao.insert_many([
        {**geral, "ano": 2025, "indice_sintetico": 53.8, "indice_metas": 53.8, "indice_acoes": float("nan"), "ano_fechado": True},
        {**geral, "ano": 2026, "indice_sintetico": 30.4, "indice_metas": float("nan"), "indice_metas_usado": 53.8,
         "ano_metas": 2025, "indice_acoes": 7.1, "ano_fechado": False},
        {"conjunto": "nucleo", "nivel": "eixo", "ano": 2025, "eixo_pls": "1", "indice_metas": 100.0, "n_com_meta": 1,
         "n_avaliados": 1, "faixa_atingida": 1},
        {"conjunto": "nucleo", "nivel": "indicador", "ano": 2025, "codigo": "N02", "indicador": "Água", "eixo_pls": "1",
         "faixa": "atingida", "alcance_pct": 100.0},
        {"conjunto": "nucleo", "nivel": "faixa", "codigo": "atingida", "faixa": "Meta atingida", "alcance_minimo": 100, "ordem": 1},
        {"conjunto": "nucleo", "nivel": "faixa", "codigo": "sem_meta", "faixa": "Sem meta", "alcance_minimo": float("nan"), "ordem": 7},
        {"conjunto": "nucleo", "nivel": "parametros", "peso_metas": 0.5, "peso_acoes": 0.5, "agregacao_metas": "eixo"},
        {"conjunto": "plano", "nivel": "geral", "ano": 2025, "indice_sintetico": 16.3},
    ]))
    asyncio.run(db.pls_eixos.insert_one({"eixo_pls": "1", "eixo": "Racionalização"}))
    r = c.get("/pls/execucao").json()
    assert r["conjunto"] == "nucleo" and r["ano"] == 2026
    assert r["ano_detalhe"] == 2025  # detalhe no ultimo ano com metas avaliadas
    atual = r["serie"][-1]
    assert (atual["indice_sintetico"], atual["indice_metas_usado"], atual["ano_metas"]) == (30.4, 53.8, 2025)
    assert r["serie"][0]["indice_acoes"] is None  # NaN vira null
    assert atual["faixas"] == {"atingida": 1, "sem_meta": 1}
    assert r["eixos"][0]["eixo"] == "Racionalização"
    assert r["indicadores"][0]["codigo"] == "N02"
    assert r["faixas"][1]["alcance_minimo"] is None
    assert c.get("/pls/execucao", params={"conjunto": "plano"}).json()["serie"][0]["indice_sintetico"] == 16.3
    assert c.get("/pls/execucao", params={"conjunto": "x"}).status_code == 422
