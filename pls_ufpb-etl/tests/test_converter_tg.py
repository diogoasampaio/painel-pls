from validacao.converter_tesouro_gerencial import converter, ler, mensal, serie

CAB = '"Ano Lançamento"\t"Natureza Despesa Detalhada"\t\t"Mês Lançamento"\t"DESPESAS LIQUIDADAS"\t"DESPESAS PAGAS"\t"06. Restos a Pagar Pagos (F)"\n'


def test_usa_periodo_de_encerramento_e_formato_brasileiro(tmp_path):
    arq = tmp_path / "tg.csv"
    arq.write_text(
        "Relatório em Branco\n\n" + CAB
        + '"2023"\t"31900101"\t"PROVENTOS"\t"NOV/2023"\t"457.237.527,16"\t"417.828.807"\t"172.140.231,89"\n'
        + '"2023"\t"31900101"\t"PROVENTOS"\t"013/2023"\t"500.579.335,05"\t"452.997.991"\t"203.438.455,87"\n'
        + '"2023"\t"31900101"\t"PROVENTOS"\t"014/2023"\t"500.579.335,05"\t"452.997.991"\t"219.087.567,86"\n'
        + '"2026"\t"33903943"\t"ENERGIA"\t"AGO/2026"\t"8,00"\t"7"\t""\n',
        encoding="latin-1",
    )
    df = converter(arq).set_index("ano")
    assert df.loc["2023", "liquidado"] == 500_579_335.05
    # RP pagos: 014 - 013 (a coluna vem com soma corrida sobre saldo acumulado)
    assert round(df.loc["2023", "pago"], 2) == round(452_997_991 + (219_087_567.86 - 203_438_455.87), 2)
    assert df.loc["2026", "pago"] == 7.0  # ano corrente: ultimo mes disponivel


def test_mensal_desfaz_acumulados(tmp_path):
    # liquidado acumulado 1, 3, 6; pagas 1, 2, 6; RP real acumulado 10, 12, 12,
    # exportado com soma corrida: 10, 22, 34
    arq = tmp_path / "tg.csv"
    arq.write_text(
        "Relatório\n\n" + CAB
        + '"2026"\t"33903943"\t"E"\t"JAN/2026"\t"1,00"\t"1"\t"10,00"\n'
        + '"2026"\t"33903943"\t"E"\t"FEV/2026"\t"3,00"\t"2"\t"22,00"\n'
        + '"2026"\t"33903943"\t"E"\t"MAR/2026"\t"6,00"\t"6"\t"34,00"\n',
        encoding="latin-1",
    )
    m = mensal(serie(ler(arq))).set_index("periodo")
    assert m["liquidado"].tolist() == [1, 2, 3]
    assert m["pago"].tolist() == [1 + 10, 1 + 2, 4 + 0]
    assert m["pago"].sum() == 6 + 12  # bate com o anual: P(ultimo) + C(ultimo)
