from faturas.combustivel import ler_nota_prime

NOTA = """QTDE UNID DISCRIMINAÇÃO DOS SERVIÇOS
4521,923 UM CONSUMO GESTAO DE FROTA GASOLINA 5,926238 26.797,99
354,608 UM CONSUMO GESTAO DE FROTA DIESEL 5,704073 2.022,71
8645,08 UM CONSUMO GESTAO DE FROTA DIESEL S10 5,771254 49.892,95
130,382 UM CONSUMO GESTAO DE FROTA GASOLINA ADITIVADA 6,257152 815,82
RETENÇÕES NA FONTE PELO TOMADOR (R$)
FATURA 2020317 - UNIVERSIDADE FEDERAL DA PARAIBA UFPB - PERIODO DE 01/06/2024 A 30/06/2024 - 005/2024"""


def test_nf_prime_da_litros_por_combustivel_no_mes_do_periodo():
    linhas = ler_nota_prime(NOTA)
    assert [x["combustivel_texto"] for x in linhas] == ["GASOLINA", "DIESEL", "DIESEL S10", "GASOLINA ADITIVADA"]
    assert {x["data"] for x in linhas} == {"2024-06-01"}
    assert round(sum(x["litros"] for x in linhas), 3) == 13651.993
    assert round(sum(x["valor_bruto"] for x in linhas), 2) == 79529.47
    assert [x["combustivel"] for x in linhas] == ["gasolina", "diesel", "diesel", "gasolina"]


def test_nf_sem_periodo_nao_vira_consumo():
    assert ler_nota_prime(NOTA.rsplit("\n", 1)[0]) == []
