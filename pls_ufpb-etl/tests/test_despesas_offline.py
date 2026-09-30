"""Caminho da API (dias sem arquivo diario publicado), ponta a ponta e offline: o cache bruto e
montado com respostas no formato do OpenAPI do Portal (DespesasPorDocumentoDTO,
DetalhamentoDoGastoDTO, EmpenhoImpactadoBasicoDTO) e o extract_transform
roda sem rede.
"""

import pytest

from common import config
from common.periodo import Janela
from common.storage import write_json

UG = "153065"
NE_ENERGIA = "153065152612025NE000010"
NE_PAPEL = "153065152612025NE000011"
NS_ENERGIA = "153065152612025NS000100"
OB_DIARIA = "153065152612025OB000200"
NS_FOLHA = "153065152612025NS000300"

BASE_DOC = {
    "categoria": "Despesas Correntes", "grupo": "Outras Despesas Correntes", "modalidade": "Aplicações Diretas",
}


@pytest.fixture
def cache(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "RAW_DIR", tmp_path / "raw")
    monkeypatch.setattr(config, "PROCESSED_DIR", tmp_path / "processed")
    monkeypatch.setattr(config, "UGS", [UG])
    raw = tmp_path / "raw" / "portal"

    def docs(fase, dia, lista):
        write_json(raw / "documentos" / UG / fase / dia[:4] / f"{dia}.json", lista)

    docs("empenho", "2025-03-03", [
        {**BASE_DOC, "documento": NE_ENERGIA, "data": "03/03/2025", "especie": "Original",
         "elemento": "Outros Serviços de Terceiros - Pessoa Jurídica", "valor": "900.000,00",
         "codigoFavorecido": "09095183000140", "nomeFavorecido": "ENERGISA PARAIBA", "observacao": "Fatura energia 2025"},
        {**BASE_DOC, "documento": NE_PAPEL, "data": "03/03/2025", "especie": "Original",
         "elemento": "Material de Consumo", "valor": "12.500,00",
         "codigoFavorecido": "11222333000144", "nomeFavorecido": "PAPELARIA X"},
    ])
    write_json(raw / "itens_empenho" / "2025" / f"{NE_ENERGIA}.json", [
        {"codigoSubelemento": "43", "descricaoSubelemento": "SERVICOS DE ENERGIA ELETRICA",
         "descricao": "Energia elétrica campus I", "valorAtual": "900.000,00", "sequencial": 1},
    ])
    write_json(raw / "itens_empenho" / "2025" / f"{NE_PAPEL}.json", [
        {"codigoSubelemento": "16", "descricaoSubelemento": "MATERIAL DE EXPEDIENTE",
         "descricao": "PAPEL A4 75G RESMA 500 FOLHAS QUANTIDADE: 500", "valorAtual": "12.500,00", "sequencial": 1},
    ])

    docs("liquidacao", "2025-03-20", [
        {**BASE_DOC, "documento": NS_ENERGIA, "data": "20/03/2025", "especie": "Original",
         "elemento": "Outros Serviços de Terceiros - Pessoa Jurídica",
         "codigoFavorecido": "09095183000140", "nomeFavorecido": "ENERGISA PARAIBA", "observacao": "Fatura fev/2025"},
        {"documento": NS_FOLHA, "data": "20/03/2025", "categoria": "Despesas Correntes",
         "grupo": "Pessoal e Encargos Sociais", "modalidade": "Aplicações Diretas",
         "elemento": "Vencimentos e Vantagens Fixas - Pessoal Civil"},
    ])
    write_json(raw / "empenhos_impactados" / "liquidacao" / "2025" / f"{NS_ENERGIA}.json", [
        {"empenho": NE_ENERGIA, "subitem": "43", "valorLiquidado": "75.300,10", "valorPago": "0,00"},
    ])

    docs("pagamento", "2025-03-25", [
        {**BASE_DOC, "documento": OB_DIARIA, "data": "25/03/2025", "especie": "Original",
         "elemento": "Diárias - Civil", "codigoFavorecido": "***.123.456-**",
         "nomeFavorecido": "FULANO DE TAL", "observacao": "Diarias do servidor Fulano"},
    ])
    write_json(raw / "empenhos_impactados" / "pagamento" / "2025" / f"{OB_DIARIA}.json", [
        {"empenho": "153065152612024NE000999", "subitem": "14", "valorPago": "0,00", "valorRestoPago": "1.020,00"},
    ])
    return tmp_path


def test_despesas_offline(cache):
    from despesas.load_despesas import COL_EMPENHOS, COL_FATO, COL_ITENS, extract_transform
    from despesas.portal_api import PortalApi
    from despesas.portal_bulk import PortalBulk

    # sem arquivo diario em cache: todos os dias caem para a API
    api = PortalApi(offline=True)
    frames, info = extract_transform(Janela.de_args("2025-03", "2025-03"), PortalBulk(offline=True), api)
    assert info["fontes"]["api"] == 31
    fato = frames[COL_FATO].set_index("documento")

    assert api.calls == 0
    # folha (319011) nao e relevante: nem busca empenhos impactados
    assert NS_FOLHA not in fato.index
    assert not any(NS_FOLHA in m for m in api.cache_misses)

    energia = fato.loc[NS_ENERGIA]
    assert energia["natureza"] == "33903943"
    assert energia["tema_codigo"] == "energia"
    assert energia["valor"] == pytest.approx(75300.10)
    assert energia["favorecido_nome"] == "ENERGISA PARAIBA"

    diaria = fato.loc[OB_DIARIA]
    assert diaria["natureza"] == "33901414"  # empenho de RP (fora da janela): natureza do documento
    assert diaria["tema_codigo"] == "deslocamento"
    assert diaria["valor"] == pytest.approx(1020.0)  # pago de restos a pagar
    # LGPD: pessoa fisica sem CPF, nome e observacao
    assert diaria["favorecido_tipo"] == "PF"
    assert diaria[["favorecido_codigo", "favorecido_nome", "observacao"]].isna().all()

    itens = frames[COL_ITENS].set_index("empenho")
    papel = itens.loc[NE_PAPEL]
    assert papel["natureza"] == "33903016"
    assert papel["regras_texto"] == ["papel_a4"]
    assert papel["quantidade_texto"] == 500
    assert len(frames[COL_EMPENHOS]) == 2
