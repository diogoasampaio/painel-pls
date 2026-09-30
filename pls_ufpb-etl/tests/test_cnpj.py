import zipfile

import pandas as pd

from cnpj import load_cnpj as m


def _zip(tmp_path, nome, linhas):
    path = tmp_path / f"{nome}.zip"
    with zipfile.ZipFile(path, "w") as z:
        z.writestr(f"{nome}.CSV", "\n".join(linhas).encode("latin-1"))
    return path


def test_filtra_empresas_pelo_cnpj_basico(tmp_path):
    z = _zip(tmp_path, "Empresas0", [
        '"11111111";"FORNECEDOR LTDA";"2062";"49";"1000,00";"01";""',
        '"22222222";"OUTRA S.A.";"2054";"10";"9,00";"05";""',
    ])
    linhas = m._filtrar(z, "Empresas", {"11111111"}, set())
    assert linhas == [{"cnpj_basico": "11111111", "razao_social": "FORNECEDOR LTDA", "natureza_juridica": "2062",
                       "porte": "01"}]


def test_filtra_estabelecimento_pelo_cnpj_completo(tmp_path):
    campos = ["" for _ in m.LAYOUT["Estabelecimentos"][0]]
    def linha(ordem, uf):
        c = list(campos)
        c[0], c[1], c[2], c[5], c[11], c[19], c[20] = "11111111", ordem, "01", "02", "4751201", uf, "2051"
        return ";".join(f'"{v}"' for v in c)
    z = _zip(tmp_path, "Estabelecimentos0", [linha("0001", "PB"), linha("0002", "SP")])
    linhas = m._filtrar(z, "Estabelecimentos", {"11111111"}, {"11111111000101"})
    assert [l["uf"] for l in linhas] == ["PB"]
    assert linhas[0]["cnpj"] == "11111111000101"


def test_categoria_do_fornecedor():
    cache = {
        "mes": "2026-09",
        "Empresas": [{"cnpj_basico": "11111111", "razao_social": "A", "natureza_juridica": "2062", "porte": "03"},
                     {"cnpj_basico": "22222222", "razao_social": "B", "natureza_juridica": "2054", "porte": "05"},
                     {"cnpj_basico": "00000000", "razao_social": "BANCO", "natureza_juridica": "2038", "porte": "05"}],
        "Estabelecimentos": [{"cnpj_basico": "11111111", "cnpj_ordem": "0001", "cnpj_dv": "01", "situacao": "02",
                              "cnae_principal": "4751201", "uf": "SP", "municipio": "7107", "cnpj": "11111111000101"},
                             {"cnpj_basico": "22222222", "cnpj_ordem": "0001", "cnpj_dv": "02", "situacao": "02",
                              "cnae_principal": "8121400", "uf": "PB", "municipio": "2051", "cnpj": "22222222000102"},
                             {"cnpj_basico": "00000000", "cnpj_ordem": "0001", "cnpj_dv": "91", "situacao": "02",
                              "cnae_principal": "6422100", "uf": "DF", "municipio": "9701", "cnpj": "00000000000191"}],
    }
    cnpjs = {"11111111000101", "22222222000102", "00000000000191", "33333333000103"}
    cat = m.categoria(m.transform(cache, cnpjs))
    assert cat.to_dict() == {
        "00000000000191": m.FINANCEIRA,
        "11111111000101": "ME/EPP de outros estados",
        "22222222000102": "Demais portes da Paraíba",
        "33333333000103": "Sem cadastro na Receita",
    }


def test_pagamentos_so_pj_em_contratacao(tmp_path, monkeypatch):
    from common import config, storage
    monkeypatch.setattr(config, "RAW_DIR", tmp_path)
    doc = {"codigo_pagamento": "P1", "codigo_favorecido": "11111111000101", "data_emissao": "05/03/2024",
           "codigo_unidade_gestora": "153065"}
    pf = {**doc, "codigo_pagamento": "P2", "codigo_favorecido": "***.123.456-**"}
    storage.write_json(tmp_path / "portal_bulk" / "2024" / "2024-03-05.json", {"ugs": [], "dados": {
        "empenho": [{"codigo_empenho": "E1", "amparo": "LEI 14.133/2021"}],
        "pagamento": [doc, pf],
        "pagamento_impactados": [
            {"codigo_pagamento": "P1", "codigo_empenho": "E1", "codigo_natureza_despesa_completa": "33903978",
             "valor_pago_r": "100,00", "valor_restos_a_pagar_pagos_r": "50,00"},
            {"codigo_pagamento": "P1", "codigo_empenho": "E1", "codigo_natureza_despesa_completa": "33904701",
             "valor_pago_r": "999,00", "valor_restos_a_pagar_pagos_r": "0,00"},
            {"codigo_pagamento": "P2", "codigo_empenho": "E1", "codigo_natureza_despesa_completa": "33903978",
             "valor_pago_r": "999,00", "valor_restos_a_pagar_pagos_r": "0,00"},
        ]}})
    df, agric = m.pagamentos_pj(("2024",))
    assert agric == set()
    assert df[["periodo", "cnpj", "natureza", "valor"]].to_dict("records") == [
        {"periodo": "2024-03", "cnpj": "11111111000101", "natureza": "33903978", "valor": 150.0}]
    assert isinstance(df, pd.DataFrame)
