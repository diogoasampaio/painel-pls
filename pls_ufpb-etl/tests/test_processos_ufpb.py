import pandas as pd

from faturas import processos_ufpb as pu


def test_dv_do_nup():
    # numeros conferidos no SIPAC
    assert pu.dv("001657", "2023") == "39"
    assert pu.dv(67042, 2024) == "41"
    assert pu.valido("045533/2024-45")
    # digitados errados no Portal (o DV ficou certo, o numero nao)
    assert not pu.valido("2001657/2023-39")
    assert not pu.valido("030265/2024-11")
    assert not pu.valido("04533/2024-45")
    assert not pu.valido("sem numero")


def _base():
    linhas = [
        ("045533", "2024", "45", "SINFRA - GERÊNCIA DE ELETRICIDADE", "APRESENTAÇÃO DAS FATURAS DE ENERGIA ELÉTRICA - CAMPUS IV"),
        ("045538", "2024", "30", "SINFRA - GERÊNCIA DE ELETRICIDADE", "APRESENTAÇÃO DAS FATURAS DE ENERGIA ELÉTRICA - CAMPUS I"),
        ("045534", "2024", "45", "PRG", "APROVEITAMENTO DE ESTUDOS"),  # mesmo DV, outro assunto
        ("030625", "2024", "11", "SULT", "FATURA GOLDI GESTÃO DE FROTA, FORNECIMENTO DE COMBUSTÍVEIS"),
    ]
    b = pd.DataFrame(linhas, columns=["num", "ano", "dv", "unidade", "assunto_detalhado"])
    return b.assign(processo=b["num"] + "/" + b["ano"] + "-" + b["dv"], interessado="", assunto="",
                    data_cadastro="2024-06-06", situacao="ATIVO")


def test_corrige_pelo_unico_candidato_com_mesmo_dv_e_assunto():
    b = _base()
    assert pu.corrigir("04533/2024-45", "energia", b) == ("045533/2024-45", [])
    assert pu.corrigir("030265/2024-11", "combustivel", b) == ("030625/2024-11", [])  # digitos trocados


def test_sem_candidato_unico_nao_corrige():
    b = _base()
    dois = pd.concat([b, b.iloc[[0]].assign(num="045553", processo="045553/2024-45")])
    certo, cands = pu.corrigir("04533/2024-45", "energia", dois)
    assert certo is None and set(cands) >= {"045533/2024-45", "045553/2024-45"}
    assert pu.corrigir("099999/2024-45", "energia", b) == (None, [])
