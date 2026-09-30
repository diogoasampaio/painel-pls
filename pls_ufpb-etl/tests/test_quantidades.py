import numpy as np
import pandas as pd
import pytest

from compras.quantidades import calcular, por_embalagem


def _item(desc, valor, regra, data="2025-04-03", emp="NE1", seq="1", qtd_txt=np.nan):
    return {"empenho": emp, "sequencial": seq, "periodo": data[:7], "ano": int(data[:4]), "mes": int(data[5:7]),
            "data": data, "ug": "153065", "descricao": desc, "valor": valor, "regras_texto": np.array([regra]),
            "quantidade_texto": qtd_txt}


COPO = "Item compra: 00016 - COPO DESCARTÁVEL, MATERIAL POLIESTIRENO, CAPACIDADE 180 ML"
CAT = pd.DataFrame([
    {"compra": "2024/324", "publicada": "2024-10-29", "numero_item": 16, "descricao_pncp": "Copo Descartável",
     "unidade_pncp": "Pacote 100,00 UN", "preco": 3.58},
    {"compra": "2025/394", "publicada": "2025-11-10", "numero_item": 17, "descricao_pncp": "Copo descartável",
     "unidade_pncp": "Unidade", "preco": 3.28},
])


@pytest.mark.parametrize("unidade, familia, esperado", [
    ("Pacote 100,00 UN", "copo", 100), ("Centena", "copo", 100), ("Caixa 2000,00 UN", "copo", 2000),
    ("Resma 500,00 FL", "papel", 1), ("Pacote 5000,00 FL", "papel", 10), ("Unidade", "toner", 1),
])
def test_unidades_por_embalagem(unidade, familia, esperado):
    assert por_embalagem(unidade, familia) == esperado


def test_quantidade_pelo_preco_da_compra_no_pncp():
    df = calcular(pd.DataFrame([_item(COPO, 179.0, "copo_descartavel")]), CAT)
    r = df.iloc[0]
    assert r["metodo"] == "pncp" and r["compra"] == "2024/324"
    assert r["embalagens"] == 50 and r["quantidade"] == 5000  # 179 / 3,58 = 50 pacotes de 100


def test_valor_que_nao_e_multiplo_do_preco_nao_casa():
    df = calcular(pd.DataFrame([_item(COPO, 180.0, "copo_descartavel")]), CAT)
    assert df.iloc[0]["metodo"] == "sem_preco" and pd.isna(df.iloc[0]["quantidade"])


def test_unidade_incompativel_com_o_preco_vira_pacote_presumido_ou_correcao():
    desc = "Item compra: 00017 - COPO DESCARTAVEL, MATERIAL POLIPROPILENO, CAPACIDADE 180 ML"
    itens = pd.DataFrame([_item(desc, 656.0, "copo_descartavel", data="2026-03-10")])
    r = calcular(itens, CAT).iloc[0]
    assert r["unidade_presumida"] and r["quantidade"] == 200 * 100  # R$ 3,28 por "unidade" de copo nao existe
    r = calcular(itens, CAT, {("2025/394", 17): 50.0}).iloc[0]
    assert not r["unidade_presumida"] and r["quantidade"] == 200 * 50


def test_sem_compra_usa_o_multiplo_dos_valores_do_item_no_ano():
    desc = "Item compra: 00015 - COPO DESCARTÁVEL, MATERIAL POLIESTIRENO, CAPACIDADE 180 ML"
    itens = pd.DataFrame([_item(desc, v, "copo_descartavel", data="2023-05-02", emp=f"NE{k}")
                          for k, v in enumerate([88.0, 572.0, 1320.0])])
    df = calcular(itens, CAT)
    assert set(df["metodo"]) == {"multiplo"} and df["preco"].iloc[0] == 44.0
    assert df["quantidade"].sum() == (2 + 13 + 30) * 100


def test_papel_fora_da_impressao_nao_entra():
    itens = pd.DataFrame([
        _item("Item compra: 00024 - PAPEL CANSON, TAMANHO A3", 50.0, "papel_a4"),
        _item("Item compra: 00029 - PAPEL PARA IMPRESSAO FORMATADO, TIPO SULFITE, 297 X 210", 250.0, "papel_a4",
              qtd_txt=10.0),
    ])
    df = calcular(itens, CAT)
    assert list(df["familia"]) == ["papel"] and df.iloc[0]["metodo"] == "texto" and df.iloc[0]["quantidade"] == 10
