"""API contra um Mongo em memoria (mongomock-motor) com documentos no
formato que o ETL grava em pls_indicadores e pls_temas.
"""

import pytest
from fastapi.testclient import TestClient
from mongomock_motor import AsyncMongoMockClient


def _ind(periodo, tema, subtema, metrica, nominal, real, unidade="R$"):
    return {
        "periodo": periodo, "ano": int(periodo[:4]), "mes": int(periodo[5:]), "tema_codigo": tema,
        "subtema": subtema, "metrica": metrica, "unidade": unidade, "valor_nominal": nominal,
        "valor_real": real, "valor_real_per_capita": real / 1000,
    }


DOCS = [
    _ind("2024-03", "energia", "Fatura de energia elétrica", "pago", 100.0, 120.0),
    _ind("2024-12", "energia", "Fatura de energia elétrica", "pago", 100.0, 110.0),
    _ind("2025-03", "energia", "Fatura de energia elétrica", "pago", 90.0, 95.0),
    _ind("2025-03", "energia", "Material elétrico (lâmpadas)", "pago", 10.0, 10.0),
    _ind("2025-12", "energia", "Fatura de energia elétrica", "pago", 90.0, 90.0),
    _ind("2026-02", "energia", "Fatura de energia elétrica", "pago", 50.0, 50.0),
    _ind("2025-03", "agua_esgoto", "Fatura de água e esgoto", "pago", 40.0, 42.0),
    _ind("2025-03", "deslocamento", "Viagens a serviço", "co2e_kg", 924.5, 924.5, "kg CO2e"),
]


@pytest.fixture
def client(monkeypatch):
    import app.db

    mock = AsyncMongoMockClient()
    monkeypatch.setattr(app.db, "AsyncIOMotorClient", lambda *_a, **_k: mock)
    from app.main import app as fastapi_app

    db = mock["painel_pls"]
    import asyncio

    async def seed():
        await db.pls_indicadores.insert_many([dict(d) for d in DOCS])
        await db.pls_temas.insert_many([
            {"tema_codigo": "energia", "tema": "Energia elétrica", "eixo_pls": "1", "ordem": 2},
            {"tema_codigo": "material_consumo", "tema": "Material de consumo", "eixo_pls": "1", "ordem": 1},
        ])

        await db.pls_eixos.insert_many([
            {"eixo_pls": "1", "eixo": "Racionalização e consumo consciente", "descricao": "..."},
            {"eixo_pls": "6", "eixo": "Divulgação e capacitação", "descricao": "..."},
        ])
        base = {"formula": "f", "meta": "m", "responsavel": "r", "rota_automacao": "rota", "tabela_pls": "16"}
        await db.pls_catalogo_indicadores.insert_many([
            {**base, "id": "E1-AGUA-01", "eixo_pls": "1", "objetivo": "OB01", "indicador": "Água per capita",
             "unidade": "m³/pessoa", "tipo_meta": "reducao_vs_base", "meta_valor": 10.0, "ano_base": 2024,
             "automacao": "integracao", "tipo_fonte": "fornecedor", "ordem": 1},
            {**base, "id": "E6-CAMPANHA-01", "eixo_pls": "6", "objetivo": "OB1", "indicador": "Campanhas",
             "unidade": "campanhas", "tipo_meta": "minimo", "meta_valor": 1.0, "ano_base": None,
             "automacao": "informado", "tipo_fonte": "documental", "ordem": 2},
            {**base, "id": "A1-CO2-01", "eixo_pls": "1", "objetivo": "Ampliação", "indicador": "CO2 aéreo",
             "unidade": "kg CO2e", "tipo_meta": "acompanhamento", "meta_valor": None, "ano_base": None,
             "automacao": "automatico", "tipo_fonte": "publica", "ordem": 3},
        ])
        await db.pls_metas.insert_many([
            {"indicador_id": "E1-AGUA-01", "eixo_pls": "1", "ano": 2025, "valor": 18.5, "origem": "lancado+comunidade",
             "fonte": "CAGEPA", "ano_completo": True, "ano_referencia": 2024, "variacao_pct": -7.5, "situacao": "nao_atingida"},
            {"indicador_id": "E1-AGUA-01", "eixo_pls": "1", "ano": 2024, "valor": 20.0, "origem": "lancado+comunidade",
             "fonte": "CAGEPA", "ano_completo": True, "ano_referencia": 2024, "variacao_pct": None, "situacao": "linha_de_base"},
        ])

        await db.pls_decisoes_comissao.insert_many([
            {"id": "D01", "indicadores": "N02|E1-AGUA-01", "questao": "Trocar o denominador?", "contexto": "c",
             "opcoes": "(a) sim (b) nao", "efeito": "e", "situacao": "pendente", "decisao": None},
        ])

        await db.pls_execucao.insert_many([
            {"conjunto": "nucleo", "nivel": "geral", "ano": 2025, "indice_sintetico": 40.0, "ano_fechado": True},
            {"conjunto": "nucleo", "nivel": "faixa", "codigo": "atingida", "faixa": "Meta atingida", "alcance_minimo": 100, "ordem": 1},
            {"conjunto": "nucleo", "nivel": "parametros", "peso_metas": 0.5, "peso_acoes": 0.5, "agregacao_metas": "eixo",
             "primeiro_ano": 2025},
            {"conjunto": "nucleo", "nivel": "indicador", "ano": 2025, "codigo": "N02", "indicador": "Água por pessoa",
             "eixo_pls": "1", "faixa": "atingida", "valor": 3.2, "ano_completo": True, "unidade": "m³/pessoa"},
            # historico: serie desde antes do 1o ano do indice
            {"conjunto": "nucleo", "nivel": "historico", "ano": 2024, "codigo": "N02", "valor": 6.5, "ano_completo": True},
            {"conjunto": "nucleo", "nivel": "historico", "ano": 2023, "codigo": "N02", "valor": 5.1, "ano_completo": True},
            {"conjunto": "nucleo", "nivel": "historico", "ano": 2025, "codigo": "N02", "valor": 3.2, "ano_completo": True},
            {"conjunto": "nucleo", "nivel": "projecao", "ano": 2026, "codigo": "N02", "valor_parcial": 1.6, "meses": 7,
             "projecao": 2.9, "metodo": "mesmo_periodo", "meta_projetada": 4.3, "regra": "reducao_vs_base",
             "sentido": "menor", "situacao_projecao": "no_rumo", "alcance_projecao": 100.0, "faixa_min": float("nan")},
        ])

    asyncio.run(seed())
    fastapi_app.state.limiter.reset()
    with TestClient(fastapi_app) as c:
        yield c


def test_paineis_e_filtros(client):
    assert {"slug": "energia", "label": "Energia elétrica"} in client.get("/pls/paineis").json()
    f = client.get("/pls/filtros").json()
    assert f["anos"] == [2024, 2025, 2026]
    assert [t["codigo"] for t in f["temas"]] == ["material_consumo", "energia"]  # ordem do CSV


def test_painel_energia_serie_anual_real(client):
    r = client.get("/pls/energia").json()
    assert r["por"] == "subtema" and r["valor"] == "real"
    fatura = {s["periodo"]: s["valor"] for s in r["series"] if s["grupo"] == "Fatura de energia elétrica"}
    assert fatura == {"2024": 230.0, "2025": 185.0, "2026": 50.0}
    # cards: 2026 esta incompleto (ultimo periodo 2026-02) -> compara 2025 x 2024
    card = next(c for c in r["destaques"] if c["grupo"] == "Fatura de energia elétrica")
    assert (card["ano"], card["ano_anterior"]) == (2025, 2024)
    assert card["variacao_pct"] == pytest.approx(-19.6)


def test_painel_mensal_nominal_e_recorte(client):
    r = client.get("/pls/energia", params={"granularidade": "mes", "valor": "nominal", "ano_inicio": 2025, "ano_fim": 2025}).json()
    assert {s["periodo"] for s in r["series"]} == {"2025-03", "2025-12"}


def test_visao_geral_quebra_por_tema(client):
    r = client.get("/pls/visao-geral").json()
    grupos = {s["grupo"] for s in r["series"]}
    assert grupos == {"energia", "agua_esgoto"}  # co2e_kg nao e metrica da visao geral


def test_painel_inexistente_e_parametro_invalido(client):
    assert client.get("/pls/nao-existe").status_code == 404
    assert client.get("/pls/energia", params={"valor": "xpto"}).status_code == 422


def test_rate_limit_60_por_minuto(client):
    codigos = [client.get("/health").status_code for _ in range(61)]
    assert codigos[:60] == [200] * 60 and codigos[60] == 429


def test_metas_catalogo_com_valores(client):
    r = client.get("/pls/metas").json()
    assert [i["id"] for i in r["indicadores"]] == ["E1-AGUA-01", "E6-CAMPANHA-01", "A1-CO2-01"]
    agua = r["indicadores"][0]
    assert [v["ano"] for v in agua["valores"]] == [2024, 2025]
    assert agua["valores"][1]["situacao"] == "nao_atingida"
    assert r["indicadores"][1]["valores"] == []  # sem lancamento ainda: aparece mesmo assim
    assert len(r["eixos"]) == 2


def test_metas_filtros(client):
    assert [i["id"] for i in client.get("/pls/metas", params={"eixo": "6"}).json()["indicadores"]] == ["E6-CAMPANHA-01"]
    assert "A1-CO2-01" not in [i["id"] for i in client.get("/pls/metas", params={"plano": True}).json()["indicadores"]]
    assert client.get("/pls/metas", params={"eixo": "9"}).status_code == 422


def test_execucao_nucleo_traz_historico_ordenado(client):
    r = client.get("/pls/execucao", params={"conjunto": "nucleo"}).json()
    n02 = next(i for i in r["indicadores"] if i["codigo"] == "N02")
    assert [h["ano"] for h in n02["historico"]] == [2023, 2024, 2025]
    assert n02["historico"][-1] == {"ano": 2025, "valor": 3.2, "ano_completo": True}
    proj = n02["projecao"]
    assert proj["ano"] == 2026 and proj["situacao_projecao"] == "no_rumo" and proj["projecao"] == 2.9
    assert proj["faixa_min"] is None  # NaN do pandas vira null


def test_card_sem_pagamento_no_ano_anterior_nao_pula_ano():
    from app.aggregation import comparar_anos

    cards = {c["grupo"]: c for c in comparar_anos([
        {"ano": 2023, "grupo": "Concurso", "valor": 100.0}, {"ano": 2025, "grupo": "Concurso", "valor": 80.0},
        {"ano": 2023, "grupo": "Limpeza", "valor": 10.0}, {"ano": 2024, "grupo": "Limpeza", "valor": 10.0},
        {"ano": 2025, "grupo": "Limpeza", "valor": 12.0},
    ])}
    assert cards["Concurso"]["ano_anterior"] == 2024 and cards["Concurso"]["variacao_pct"] is None
    assert cards["Limpeza"]["variacao_pct"] == pytest.approx(20.0)
    # primeiro ano da serie: nao ha ano anterior carregado
    assert comparar_anos([{"ano": 2023, "grupo": "X", "valor": 1.0}])[0]["ano_anterior"] is None


def test_decisoes_da_comissao_na_descricao_dos_indicadores(client):
    metas = client.get("/pls/metas").json()["indicadores"]
    agua = next(i for i in metas if i["id"] == "E1-AGUA-01")
    assert [d["id"] for d in agua["decisoes"]] == ["D01"] and agua["decisoes"][0]["situacao"] == "pendente"
    assert next(i for i in metas if i["id"] == "E6-CAMPANHA-01")["decisoes"] == []
    n02 = next(i for i in client.get("/pls/execucao", params={"conjunto": "nucleo"}).json()["indicadores"]
               if i["codigo"] == "N02")
    assert [d["id"] for d in n02["decisoes"]] == ["D01"]  # citada pelo Nxx e pelo id do catalogo: uma vez so
