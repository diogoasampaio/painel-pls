from types import SimpleNamespace

import pandas as pd
import pytest

from execucao.projecao import meta_do_ano, projetar, situacao


def _regra(regra, parametro=None, ano_base="", sentido="menor"):
    return SimpleNamespace(regra=regra, parametro=parametro, ano_base=ano_base, sentido=sentido)


VALS = {2023: (90.0, True), 2024: (100.0, True), 2025: (80.0, True), 2026: (30.0, False)}


def test_metas_por_regra():
    assert meta_do_ano(_regra("reducao_anual", 2.5, "2024"), VALS, 2026)[0] == pytest.approx(100 * 0.975**2)
    assert meta_do_ano(_regra("reducao_vs_base", 10, "2024"), VALS, 2026)[0] == pytest.approx(90)
    assert meta_do_ano(_regra("minimo", 70), VALS, 2026)[0] == 70
    assert meta_do_ano(_regra("manter", None, "2023-2025"), VALS, 2026)[0] == pytest.approx(90)
    meta, faixa = meta_do_ano(_regra("faixa", 10, "2023-2025", "faixa"), VALS, 2026)
    assert faixa == pytest.approx((81, 99))
    # ano base incompleto nao serve de base
    assert meta_do_ano(_regra("manter", None, "2026"), VALS, 2026)[0] is None


def test_projecao_pelo_mesmo_periodo_do_ano_anterior():
    # 2025: 10 por mes (120 no ano); 2026: 12 por mes ate marco -> +20% sobre 2025
    base = pd.DataFrame({
        "metrica": "consumo_m3", "tema_codigo": "agua", "subtema": "Campus I", "ano": [2025] * 12 + [2026] * 3,
        "mes": list(range(1, 13)) + [1, 2, 3], "valor_nominal": [10.0] * 12 + [12.0] * 3,
    })
    calc = {"metrica": "consumo_m3", "tema": None, "subtemas": [], "campo": "valor_nominal"}
    p = projetar(calc, {2025: (120.0, True), 2026: (36.0, False)}, base, 2026)
    assert p["metodo"] == "mesmo_periodo" and p["meses"] == 3
    assert p["projecao"] == pytest.approx(144)


def test_situacao_pelo_sentido():
    menor, maior = _regra("x", sentido="menor"), _regra("x", sentido="maior")
    assert situacao(menor, 100, None, 95)[0] == "no_rumo"
    assert situacao(menor, 100, None, 105)[0] == "atencao"
    assert situacao(menor, 100, None, 130)[0] == "fora_do_rumo"
    assert situacao(maior, 70, None, 65)[0] == "atencao"
    assert situacao(maior, 70, None, 40) == ("fora_do_rumo", pytest.approx(57.1, abs=0.1))
    assert situacao(maior, 70, None, None)[0] == "sem_dado"
    assert situacao(_regra("x", 15, sentido="faixa"), 100, (85, 115), 110)[0] == "no_rumo"


def test_base_do_mesmo_periodo_muito_pequena_vira_anualizado():
    # 2025 comprou quase tudo em dezembro: jan-mar/2025 = 1 de 120 no ano; 2026 = 30 ate marco
    base = pd.DataFrame({
        "metrica": "consumo_m3", "tema_codigo": "agua", "subtema": "Campus I", "ano": [2025] * 4 + [2026] * 3,
        "mes": [1, 2, 3, 12, 1, 2, 3], "valor_nominal": [1.0, 0.0, 0.0, 119.0, 10.0, 10.0, 10.0],
    })
    calc = {"metrica": "consumo_m3", "tema": None, "subtemas": [], "campo": "valor_nominal"}
    p = projetar(calc, {2025: (120.0, True), 2026: (30.0, False)}, base, 2026)
    assert p["metodo"] == "anualizado" and p["projecao"] == pytest.approx(120)
