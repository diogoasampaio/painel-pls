import pandas as pd
import pytest

from common import config
from common.storage import save_processed


@pytest.fixture
def processed(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "PROCESSED_DIR", tmp_path)
    save_processed(pd.DataFrame({
        "periodo": ["2024-01", "2024-02"], "ano": [2024, 2024], "variacao_pct": [0.0, 10.0], "indice": [1.0, 1.1],
    }), "pls_ipca")
    save_processed(pd.DataFrame({
        "ano": [2023], "co_ies": ["579"], "comunidade": [1000], "ufpb": [True],
    }), "pls_comunidade")
    save_processed(pd.DataFrame({
        "periodo": ["2024-01", "2024-01", "2024-02"],
        "tema_codigo": ["energia", "energia", "energia"],
        "subtema": ["Fatura de energia elétrica"] * 3,
        "fase": ["liquidacao", "liquidacao", "pagamento"],
        "valor": [100.0, 50.0, 80.0],
    }), "pls_despesas")


def test_deflator_e_per_capita(processed):
    from indicadores.build_indicadores import build

    df = build().set_index(["periodo", "metrica"])
    jan = df.loc[("2024-01", "liquidado")]
    assert jan["valor_nominal"] == 150
    assert jan["valor_real"] == pytest.approx(165)  # a precos de 2024-02 (indice 1.1)
    assert jan["ref_ipca"] == "2024-02"
    assert jan["ano_comunidade"] == 2023  # censo 2024 ainda nao publicado: usa o ultimo
    assert jan["valor_real_per_capita"] == pytest.approx(0.165)
    fev = df.loc[("2024-02", "pago")]
    assert fev["valor_real"] == pytest.approx(80)


def test_tema_vem_da_tabela_vigente(processed):
    from indicadores.build_indicadores import build

    # parquet gravado com a classificacao antiga: manutencao predial era "contratacoes"
    save_processed(pd.DataFrame({
        "periodo": ["2024-01"], "tema_codigo": ["contratacoes"], "subtema": ["Manutenção predial"],
        "fase": ["pagamento"], "valor": [10.0], "natureza": ["33903916"],
    }), "pls_despesas")
    df = build()
    assert set(df["tema_codigo"]) == {"manutencao_predial"}


def test_consumo_por_campus_e_por_m2(processed):
    from indicadores.build_indicadores import build

    save_processed(pd.DataFrame({
        "processo": ["1/2024-1", "1/2024-1", "2/2024-2"], "tipo": ["energia", "energia", "agua"],
        "campus": ["IV", "IV", "I"], "status": ["ok"] * 3, "periodo": ["2024-01"] * 3,
        "kwh": [1000.0, 125.0, None], "m3": [None, None, 353.2],
    }), "pls_faturas")
    df = build().set_index(["metrica", "subtema"])
    kwh = df.loc[("consumo_kwh", "Campus IV")]
    assert kwh["valor_nominal"] == 1125 and kwh["unidade"] == "kWh"
    assert kwh["area_m2"] == 22500  # Rio Tinto + Mamanguape
    assert kwh["valor_por_m2"] == pytest.approx(0.05)
    assert df.loc[("consumo_m3", "Campus I"), "valor_por_m2"] == pytest.approx(0.001)  # 353.200 m2
    # despesa sem campus: area total da UFPB
    assert df.loc[("liquidado", "Fatura de energia elétrica"), "area_m2"] == 490700


def test_capacitacao_por_acao_e_concurso_separado():
    from indicadores import build_indicadores as b

    df = pd.DataFrame([
        # concurso publico pago na natureza de selecao e treinamento: nao e capacitacao
        {"natureza": "33903948", "acao": "20RK", "observacao": "REALIZACAO DE CONCURSO PUBLICO", "favorecido_nome": "IBFC"},
        {"natureza": "33903948", "acao": "20RK", "observacao": "CURSO DE LICITACOES", "favorecido_nome": "ESAFI"},
        {"natureza": "33903948", "acao": "4572", "observacao": "CURSO", "favorecido_nome": "X"},
    ])
    b._separar_selecao(df, df["acao"])
    assert df["subtema"].tolist() == ["Concurso e seleção", "Treinamento (outras ações)", "Serviços de treinamento (ação 4572)"]


def test_gee_escopos_e_misturas(monkeypatch):
    from indicadores import build_indicadores
    from indicadores.build_indicadores import _gee

    monkeypatch.setattr(build_indicadores, "_fatores_sin", lambda: {})  # sem a planilha do MCTI: anual do ref

    base = pd.DataFrame([
        # abr/2023: diesel B12 -> 88% fossil; gasolina E27 -> 73% fossil
        {"periodo": "2023-04", "metrica": "consumo_litros", "subtema": "Frota - diesel S10", "valor": 100.0},
        {"periodo": "2023-04", "metrica": "consumo_litros", "subtema": "Frota - gasolina", "valor": 100.0},
        {"periodo": "2023-04", "metrica": "consumo_litros", "subtema": "Frota - etanol", "valor": 100.0},
        {"periodo": "2023-04", "metrica": "consumo_kwh", "subtema": "Campus I", "valor": 1000.0},
        {"periodo": "2027-04", "metrica": "consumo_kwh", "subtema": "Campus I", "valor": 1000.0},  # sem fator no ref: ultimo anual (2025), provisorio
        {"periodo": "2023-04", "metrica": "co2e_kg", "subtema": "Viagens a serviço", "valor": 50.0},
    ])
    g = _gee(base).set_index(["periodo", "subtema"])["valor"]
    assert g[("2023-04", "Escopo 1 · frota (diesel)")] == pytest.approx(100 * 0.88 * 2.677)
    assert g[("2023-04", "Escopo 1 · frota (gasolina)")] == pytest.approx(100 * 0.73 * 2.278)
    assert g[("2023-04", "Escopo 2 · energia elétrica")] == pytest.approx(1000 * 0.0385)
    assert g[("2027-04", "Escopo 2 · energia elétrica")] == pytest.approx(1000 * 0.0461)
    assert g[("2023-04", "Escopo 3 · viagens aéreas")] == pytest.approx(50)
    assert not any("etanol" in s for _, s in g.index)  # CO2 do etanol e biogenico


def test_diesel_s10_e_comum():
    from indicadores.build_indicadores import _subtema_combustivel

    comb = pd.DataFrame({"combustivel": ["diesel", "diesel", "diesel", "gasolina"],
                         "combustivel_texto": ["DIESEL S10", "DieselS10", "DIESEL COMUM", "GASOLINA"]})
    assert _subtema_combustivel(comb).tolist() == [
        "Frota - diesel S10", "Frota - diesel S10", "Frota - diesel comum", "Frota - gasolina"]
