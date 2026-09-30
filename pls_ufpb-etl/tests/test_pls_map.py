from common import pls_map
from common.periodo import Janela
from common.text import parse_valor


def test_natureza6_aceita_nome_ou_codigo():
    por_nome = pls_map.natureza6(
        "Despesas Correntes", "Outras Despesas Correntes", "Aplicações Diretas",
        "Outros Serviços de Terceiros - Pessoa Jurídica",
    )
    por_codigo = pls_map.natureza6("3 - Despesas Correntes", "3", "90 - Aplicações Diretas", "39 - Outros Servicos")
    assert por_nome == por_codigo == "339039"


def test_natureza6_tolera_variacao_de_redacao():
    assert pls_map.natureza6("Despesas Correntes", "Outras Despesas Correntes", "Aplicações Diretas", "Diárias - Pessoal Civil") == "339014"


def test_natureza8_formatos_de_subitem():
    assert pls_map.natureza8("339039", "43") == "33903943"
    assert pls_map.natureza8("339039", "43 - SERVICOS DE ENERGIA ELETRICA") == "33903943"
    assert pls_map.natureza8("339039", "39.43") == "33903943"
    assert pls_map.natureza8(None, "33903944") == "33903944"
    assert pls_map.natureza8("339039", None) is None


def test_classificacao_prefixo_mais_longo():
    assert pls_map.classificar_natureza("33903943").tema_codigo == "energia"
    assert pls_map.classificar_natureza("33901414").tema_codigo == "deslocamento"  # prefixo 339014
    assert pls_map.classificar_natureza("33903999").tema_codigo == pls_map.NAO_CLASSIFICADO
    assert pls_map.classificar_natureza(None).tema_codigo == pls_map.NAO_CLASSIFICADO


def test_elemento_relevante_filtra_chamadas():
    assert pls_map.elemento_relevante("339039")
    assert pls_map.elemento_relevante("339014")
    assert not pls_map.elemento_relevante("319011")  # folha de pessoal
    assert pls_map.elemento_relevante(None)  # sem natureza: busca por seguranca


def test_regras_texto():
    regras = lambda t: {r["regra"] for r in pls_map.classificar_texto(t)}  # noqa: E731
    assert regras("PAPEL A4, 75G/M2, BRANCO, RESMA C/ 500 FOLHAS") == {"papel_a4"}
    assert regras("Copo descartável 200ml, pacote com 100") == {"copo_descartavel"}
    assert regras("LÂMPADA TUBULAR LED 18W") == {"lampada_led"}
    assert "fotovoltaica" in regras("Aquisição de sistema fotovoltaico on-grid")
    assert regras("Serviço de coleta de resíduos de saúde") == {"residuos"}
    assert regras("Cadeira giratória") == set()


def test_quantidade_no_texto():
    assert pls_map.quantidade_no_texto("PAPEL A4 ... QUANTIDADE: 1.200 VALOR UNITARIO: 25,00") == 1200
    assert pls_map.quantidade_no_texto("Qtd 50 unidades") == 50
    assert pls_map.quantidade_no_texto("sem quantidade informada") is None


def test_parse_valor():
    assert parse_valor("1.234,56") == 1234.56
    assert parse_valor("-10,00") == -10.0
    assert parse_valor("1234.5") == 1234.5
    assert parse_valor("") is None


def test_janela_padrao_dois_meses_fechados():
    from datetime import date

    j = Janela.de_args(None, None, hoje=date(2026, 9, 23))
    assert j.meses() == ["2026-07", "2026-08"]
    assert Janela.de_args("2025-11", "2026-02").meses() == ["2025-11", "2025-12", "2026-01", "2026-02"]
    assert len(Janela.de_args("2024-02", "2024-02").dias()) == 29
