import pandas as pd
import pytest

from execucao import build_execucao as e
from metas.load_metas import _situacao, alcance, faixa_de


@pytest.mark.parametrize("tipo,meta,valor,var,sit,esperado", [
    ("minimo", 10, 7.5, None, "nao_atingida", 75.0),
    ("minimo", 10, 12, None, "atingida", 100.0),
    ("maximo", 50, 80, None, "nao_atingida", 62.5),
    ("reducao_anual", 2.5, 100, -1.0, "nao_atingida", 40.0),
    ("reducao_anual", 2.5, 100, 2.7, "nao_atingida", 0.0),  # piorou
    ("aumento_vs_base", 20, 100, 15.0, "nao_atingida", 75.0),
    ("booleano", 1, 0, None, "nao_atingida", 0.0),
    ("minimo", 10, 5, None, "em_andamento", None),  # ano parcial: sem alcance
])
def test_alcance(tipo, meta, valor, var, sit, esperado):
    assert alcance(tipo, meta, valor, var, sit) == esperado


def test_faixas():
    assert faixa_de(100, "minimo", "atingida") == "atingida"
    assert faixa_de(80, "minimo", "nao_atingida") == "proxima"
    assert faixa_de(50, "minimo", "nao_atingida") == "progresso"
    assert faixa_de(10, "minimo", "nao_atingida") == "distante"
    assert faixa_de(None, "minimo", "linha_de_base") == "nao_avaliavel"
    assert faixa_de(None, "minimo", None) == "sem_dado"
    assert faixa_de(None, "acompanhamento", "acompanhamento") == "sem_meta"


def test_aumento_e_maximo_na_situacao():
    serie = {2024: 100.0, 2025: 125.0}
    base = {"ano": 2025, "tipo_meta": "aumento_vs_base", "meta_valor": 20, "ano_base": 2024}
    assert _situacao(base, serie, {2024: True, 2025: True})[2] == "atingida"
    assert _situacao({**base, "tipo_meta": "maximo", "meta_valor": 120}, serie, {2025: True})[2] == "nao_atingida"


def test_indice_metas_media_por_eixo():
    df = pd.DataFrame({"eixo_pls": ["1", "1", "1", "2"], "alcance_pct": [100.0, 100.0, 100.0, 0.0]})
    assert e._indice_metas(df, "eixo") == 50.0  # eixo 1 = 100, eixo 2 = 0
    assert e._indice_metas(df, "indicador") == 75.0


def test_sintetico_renormaliza_componente_faltante():
    p = {"peso_metas": 0.5, "peso_acoes": 0.5}
    assert e._sintetico(60.0, 20.0, p) == (40.0, "metas+acoes")
    assert e._sintetico(60.0, None, p) == (60.0, "metas")
    assert e._sintetico(None, None, p) == (None, "")
