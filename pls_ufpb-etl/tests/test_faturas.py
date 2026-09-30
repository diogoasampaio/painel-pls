from pathlib import Path

import pdfplumber
import pytest

from faturas.leitores import ler_cagepa_texto, ler_resumo_energisa, medido_da_pagina

FIX = Path(__file__).parent / "fixtures"


def test_resumo_energisa_com_nome_sobreposto():
    # pagina 1 real (Campus III, dez/2023): nomes longos invadem Ref. e kWh
    with pdfplumber.open(FIX / "energisa_resumo_campus3_2023-12.pdf") as pdf:
        ucs = {u["uc"]: u for u in ler_resumo_energisa(pdf.pages[0])}
    assert set(ucs) == {"308029", "1072048", "1574199", "9980518"}
    assert ucs["308029"]["kwh_faturado"] == 3687  # impresso sob 'NEGRE3IR68O7S'
    assert ucs["1072048"]["kwh_faturado"] == pytest.approx(3597.899999)
    assert ucs["9980518"]["kwh_faturado"] == pytest.approx(57533.868)
    assert ucs["9980518"]["demanda_kw"] == 185
    assert ucs["9980518"]["valor_bruto"] == pytest.approx(37690.37)
    assert {u["referencia"] for u in ucs.values()} == {"12/2023"}


def test_medido_da_danf3e():
    grupo_a = (
        "MATRÍCULA: 0009980564-2023-12-5 Data de Apresentação:\n"
        "00009028031 Energia ativa em kWh Ponta 2743,972 2784,091 210 8424,99\n"
        "00009028031 Energia ativa em kWh Fora Ponta 24233,435 24625,007 210 82230,12\n"
    )
    assert medido_da_pagina(grupo_a) == ("9980564", pytest.approx(90655.11))
    grupo_b = "MATRÍCULA: 144724-2024-4-2\nX Energia ativa em kWh Ponta 60256 61111 1 855\n"
    assert medido_da_pagina(grupo_b) == ("144724", 855)
    assert medido_da_pagina("sem quadro de medicao") is None


def test_fatura_agrupada_cagepa():
    texto = (
        "FATURA AGRUPADA\nCOMPANHIA DE AGUAS E ESGOTOS DA PARAIBA\n"
        "UFPB RIO TINTO E MAMANGUAPE - CAMPUS IV AVENIDA SANTA ELIZABETH - 160 - CENTRO RIO TINTO PB 58297-000 "
        "24.098.477/0017-87 25/01/2024 08:09 63458 10804 01/2024 15/02/2024 1 /2\n"
        "69112720 B19N000123 UFPB - CAMPUS IV 16367 16649 282 15/02/2024 1 LIG LIG ÁGUA 1.000,00\n"
        "69725233 A21AA011111 UFPB-LN 8337 8612 275 275 15/02/2024 1 LIG LIG ÁGUA 900,00\n"
        "VALOR POR EXTENSO TOTAL DE CONTAS TOTAL BRUTO: 8.634,55 TOTAL A PAGAR\n"
    )
    f = ler_cagepa_texto(texto)
    assert (f["fatura"], f["valor_bruto"]) == ("63458", 8634.55)
    lig = {u["uc"]: u for u in f["unidades"]}
    assert lig["69112720"]["m3_medido"] == 282 and lig["69112720"]["m3_faturado"] is None
    assert lig["69725233"]["m3_faturado"] == 275
    assert {u["referencia"] for u in f["unidades"]} == {"2024-01"}
    assert ler_cagepa_texto("outra coisa") is None


def test_resumo_energisa_formato_2026():
    # numero da UC com pontuacao ('307.568.053-41') e nome sobre a coluna kWh ('3U4F2P9B' = 3429)
    with pdfplumber.open(FIX / "energisa_resumo_campus1_2026-03.pdf") as pdf:
        ucs = {u["uc"]: u for u in ler_resumo_energisa(pdf.pages[0])}
    assert len(ucs) == 13
    assert ucs["66866905337"]["kwh_faturado"] == 3429
    assert ucs["4702405373"]["kwh_faturado"] == pytest.approx(1364422.5)  # ponta + fora ponta da DANF3E
    assert {u["referencia"] for u in ucs.values()} == {"03/2026"}


def test_cagepa_ligacao_grudada_no_hidrometro():
    texto = (
        "FATURA AGRUPADA\nCOMPANHIA DE AGUAS E ESGOTOS DA PARAIBA\n"
        "UFPB JOAO PESSOA - CAMPUS I X 24.098.477/0001-10 28/04/2025 07:08 71465 1457 04/2025 15/05/2025 1 /2\n"
        "81000A21AA0385351 UFPB JOAO PESSOA - CAMPUS I 4646 4611 217 15/05/2025 1 LIG LIG ÁGUA 3.684,22\n"
        "84875B21SG0013803 CASA E U FEMININA 1922 2103 181 181 15/05/2025 1 LIG LIG ÁGUA 3.061,42\n"
    )
    lig = {u["uc"]: u for u in ler_cagepa_texto(texto)["unidades"]}
    assert set(lig) == {"81000", "84875"}
    assert lig["81000"]["m3_medido"] == 217 and lig["84875"]["m3_faturado"] == 181


def test_fatura_suspeita_pela_tarifa():
    from faturas.load_faturas import suspeito

    ok = {"tipo": "energia", "unidades": [{"kwh_faturado": 60209.3, "kwh_medido": 60209.3, "valor_bruto": 43793.55}]}
    corte = {"tipo": "energia", "unidades": [{"kwh_faturado": 209.297, "kwh_medido": None, "valor_bruto": 43793.55}]}
    colado = {"tipo": "energia", "unidades": [{"kwh_faturado": 60209.3, "kwh_medido": 42053664.1, "valor_bruto": 43793.55}]}
    minimo = {"tipo": "energia", "unidades": [{"kwh_faturado": 100, "kwh_medido": 34, "valor_bruto": 94.82}]}
    assert not suspeito(ok) and not suspeito(minimo)
    assert suspeito(corte) and suspeito(colado)


def test_numero_do_processo_nos_formatos_do_portal():
    from faturas.load_faturas import normalizar_processo

    assert normalizar_processo("004049/2024-54") == "004049/2024-54"
    assert normalizar_processo("23074.017294/2026-72") == "017294/2026-72"
    assert normalizar_processo("009815/2026-51.") == "009815/2026-51"
    assert normalizar_processo("042864/2024-3752") == "042864/2024-37"  # DV so com 2 digitos
    assert normalizar_processo("23074017371202630") == "017371/2026-30"  # so digitos, com radical
    assert normalizar_processo("027309202606") == "027309/2026-06"  # so digitos, sem radical
    assert normalizar_processo("sem numero") is None


class _Pagina:
    def __init__(self, texto):
        self.texto = texto

    def extract_text(self):
        return self.texto


class _Pdf:
    def __init__(self, *textos):
        self.pages = [_Pagina(t) for t in textos]


def test_extrato_goldi():
    # layout real do extrato GOLDI (texto sem espacos); nomes ficticios
    from faturas.combustivel import ler_extrato_goldi

    pdf = _Pdf(
        "EXTRATO DE FATURAMENTO\nDepartamento: CCA(24.098.477/0001-10)\nFatura: Faturan90936de01/01/2024(ID:90936)\n"
        "DETALHAMENTO DA FATURA\nDieselS10\n"
        "01/12/2313:13 CORINGA/CORINGA-COR-0007 FulanodeTal POSTOSAOJOSEPB 68,000 6,010 408,68 16,55 392,13\n"
        "Oliveira SERVICOS-CENTRO\nGasolinaComum\n"
        "05/12/2307:19 VW/GOL-QFF-2030 BeltranoSilva REDESANTARITA 21,867 5,580 122,02 4,94 117,08\n"
        "1,000 R$0,00 R$0,00 R$0,00\n",
        "EXTRATO DE FATURAMENTO\nDepartamento: SULT(24.098.477/0001-10)\n(ID:90940)\nDieselS10\n"
        "06/12/2308:06 VW/MASCARELO-QFO-4226 Ciclano POSTOPIOXII 1.100,000 6,010 6.611,00 267,74 6.343,26\n",
    )
    linhas = ler_extrato_goldi(pdf)
    assert [(r["subunidade"], r["combustivel"], r["data"]) for r in linhas] == [
        ("CCA", "diesel", "2023-12-01"), ("CCA", "gasolina", "2023-12-05"), ("SULT", "diesel", "2023-12-06")]
    assert linhas[1]["placa"] == "QFF-2030"
    assert linhas[2]["litros"] == pytest.approx(1100.0)
    assert linhas[2]["valor_liquido"] == pytest.approx(6343.26)
    assert len({r["transacao"] for r in linhas}) == 3
    assert "condutor" not in linhas[0] and linhas[0]["estabelecimento"] is None  # LGPD: sem motorista


def _cabecalho(pares, y=100.0):
    return [{"text": t, "x0": float(x), "top": y} for t, x in pares]


def test_layout_relatorio_abastecimento_2025():
    from faturas.combustivel import _limites

    cab = _cabecalho([("Códig", 32), ("Data", 55), ("Hora", 76), ("Placa", 96), ("Prefix", 117), ("Km/H", 265),
                      ("Quan", 287), ("Preço", 307), ("Valor", 329), ("Unida", 392), ("Subu", 414), ("Servi", 435),
                      ("Nome", 455), ("CNPJ", 476), ("Cidad", 518), ("KM/H", 540), ("KM", 564), ("Valor", 709)])
    _, cols = _limites(cab)
    nomes = dict(cols)
    assert {v: k for k, v in nomes.items() if v}["preco_litro"] == pytest.approx((287 + 307) / 2)
    assert {v for v in nomes.values() if v} >= {"litros", "subunidade", "combustivel", "km_rodado", "km_por_litro"}


def test_layout_conferencia_nfe_anp():
    # dez/2025: valores comecam ate 8 pt antes do cabecalho; 'Cód Venda', 'Nome Posto' sao uma coluna so
    from faturas.combustivel import _limites

    cab = _cabecalho([("Cód", 34), ("Venda", 47), ("Data", 82), ("Hora", 121), ("KM", 162), ("Modelo", 195),
                      ("Placa", 237), ("Nº", 276), ("do", 285), ("Matrícula", 310), ("Condutor", 349),
                      ("Unidade", 390), ("Nome", 423), ("Posto", 441), ("Cidade", 470), ("Combustíve", 502),
                      ("Qtde", 551), ("Valor", 589), ("Valor", 621), ("Litro", 638), ("ANP", 669), ("Valor", 703),
                      ("c/", 720), ("Valor", 746), ("Taxa", 786)])
    _, cols = _limites(cab)
    coluna = lambda x: max((c for c in cols if x >= c[0]), key=lambda c: c[0])[1]  # noqa: E731
    assert coluna(43) == "transacao" and coluna(74) == "data" and coluna(231) == "placa"
    assert coluna(370) is None and coluna(386) == "subunidade"  # 'DE' do nome do condutor x 'CAMPUS'
    assert coluna(550) == "litros" and coluna(744) == "valor_liquido"


def test_medicao_residuos_bgreen():
    from faturas.leitores import ler_residuos_texto

    texto = (
        "RELATORIO DE FISCALIZACAO - MENSAL\nContrato 3 ADITIVO UFPB/SOF 001/2025 Periodo: 01/02/2026 a 28/02/2026\n"
        "01/02/2026 a Coleta, transporte, tratamento e destinacao final de residuos dos grupos A, B e\n"
        "UFPB CAMPUS I 1760,08 Kg R$ 5,47 R$ 9.627,64\n28/02/2026 E\n"
        "UFPB CAMPUS II 402,30 Kg R$ 5,47 R$ 2.200,60\n"
        "UFPB CAMPUS III 352,02 Kg R$ 5,47 R$ 1.925,53\nQtd. Total de servicos: 2514,4 Kg\n"
    )
    r = ler_residuos_texto(texto.replace("Periodo", "Período"))
    assert [(u["uc"], u["referencia"], u["kg"]) for u in r["unidades"]] == [
        ("CAMPUS I", "2026-02", 1760.08), ("CAMPUS II", "2026-02", 402.30), ("CAMPUS III", "2026-02", 352.02)]
    assert sum(u["valor_bruto"] for u in r["unidades"]) == pytest.approx(13753.77)


def test_extrato_goldi_antigo():
    # dez/2022: produto no inicio da linha, so qtde/unitario/total; taxa e desconto ficam de fora
    from faturas.combustivel import ler_extrato_goldi

    class P:
        def __init__(self, t):
            self.t = t

        def extract_text(self):
            return self.t

    pdf = type("Pdf", (), {"pages": [P(
        "EXTRATO DE FATURAMENTO\nDepartamento: SULT(24.098.477/0001-10)\nFatura: Faturan72461(ID:72461)\n"
        "DieselS10 16/12/2209:37 CHEVROLET/S10-NQI-3920FulanoDeTal MASTERGASREMIGIO 35,000 6,380 223,30\n"
        "35,000 R$223,30\n"
        "GasolinaComum 05/12/2210:20 GM/CORSASEDAN- Beltrano POSTOSAOJOSEPB 39,000 4,770 186,03\n"
        "TaxadeAdministracao 01/01/2300:30 - 1,000 0,000 0,00\n"
        "Descontopadraosobrecombustiveis! 01/01/2300:30 - 1,000 -24,650 -24,65\n")]})()
    linhas = ler_extrato_goldi(pdf)
    assert [(r["combustivel"], r["data"], r["litros"]) for r in linhas] == [
        ("diesel", "2022-12-16", 35.0), ("gasolina", "2022-12-05", 39.0)]
    assert linhas[0]["placa"] == "NQI-3920" and linhas[0]["valor_liquido"] is None


def test_planilha_consumo_goldi():
    # fatura de mar/2023 veio escaneada: a planilha "Analise de Consumo da Frota" tem o texto
    from faturas.combustivel import ler_planilha_goldi

    class P:
        def __init__(self, t):
            self.t = t

        def extract_text(self):
            return self.t

    pdf = type("Pdf", (), {"pages": [P(
        "CLIENTE_NOME VEICULO_MODELO VEICULO_PLACA DATAHORA MOTORISTA_NOME REDE_NOME PRODUTO_NOME QUANTIDADE VALOR_UNITARIO VALOR_TOTAL\n"
        "COUTINHO E COUTINHO LTDA-ME - SAO\n"
        "UNIVERSIDADE FEDERAL DA PARAIBA- UFPBCHEVROLET/SPIN OFA-6531 01/03/2023 07:10FULANO DE TAL JOSE PB Gasolina Comum 42,46 R$ 4,97 R$ 211,03\n"
        "UNIVERSIDADE FEDERAL DA PARAIBA- UFPB MARCOPOLO/VOLARE NPX-6379 01/06/2023 06:56BELTRANO JOSE PB JOAO PESSOA Diesel S10 70 R$ 4,93 R$ 345,10\n"
        "TOTAL R$ 556,13\n")]})()
    linhas = ler_planilha_goldi(pdf)
    assert [(r["placa"], r["data"], r["combustivel"], r["litros"]) for r in linhas] == [
        ("OFA-6531", "2023-03-01", "gasolina", 42.46), ("NPX-6379", "2023-06-01", "diesel", 70.0)]
    assert linhas[1]["combustivel_texto"] == "Diesel S10" and linhas[0]["subunidade"] is None
