"""Caminho dos arquivos diarios (dados abertos): um zip montado com os
cabecalhos reais do Portal (conferidos no arquivo de 15/01/2025) passa pelo
filtro da UFPB e pela normalizacao, sem rede.

O cabecalho do Pagamento e do Pagamento_EmpenhosImpactados nao foi visto no
arquivo real; segue o padrao da Liquidacao (ver _exigir, que falha com a
lista de colunas recebidas se divergir).
"""

import io
import zipfile

import pytest

from common import config
from common.periodo import Janela
from common.storage import raw_path, write_json

UG = "153065"
OUTRA_UG = "154040"
DIA = "20250115"

EMPENHO = (
    '"Id Empenho";"Código Empenho";"Código Empenho Resumido";"Data Emissão";"Código Tipo Documento";"Tipo Documento";'
    '"Tipo Empenho";"Espécie Empenho";"Código Órgão Superior";"Órgão Superior";"Código Órgão";"Órgão";'
    '"Código Unidade Gestora";"Unidade Gestora";"Código Gestão";"Gestão";"Código Favorecido";"Favorecido";"Observação";'
    '"Código Categoria de Despesa";"Categoria de Despesa";"Código Grupo de Despesa";"Grupo de Despesa";'
    '"Código Modalidade de Aplicação";"Modalidade de Aplicação";"Código Elemento de Despesa";"Elemento de Despesa";'
    '"Valor Original do Empenho";"Valor do Empenho Convertido pra R$";"Valor Utilizado na Conversão"\n'
    f'"1";"{UG}152612025NE000011";"2025NE000011";"15/01/2025";"NE";"Empenho";"Ordinário";"Original";"26000";"MEC";"26240";"UFPB";'
    f'"{UG}";"UFPB";"15231";"UFPB";"11222333000144";"PAPELARIA X";"Material de expediente";'
    '"3";"Despesas Correntes";"3";"Outras Despesas Correntes";"90";"Aplicações Diretas";"30";"Material de Consumo";'
    '"12500,00";"12500,00";"0"\n'
    f'"2";"{OUTRA_UG}152612025NE000001";"2025NE000001";"15/01/2025";"NE";"Empenho";"Ordinário";"Original";"26000";"MEC";"26999";"Outra";'
    f'"{OUTRA_UG}";"Outra";"15231";"Outra";"11222333000144";"X";"";'
    '"3";"Despesas Correntes";"3";"Outras Despesas Correntes";"90";"Aplicações Diretas";"30";"Material de Consumo";'
    '"1,00";"1,00";"0"\n'
)
ITEM = (
    '"Id Empenho";"Código Empenho";"Código Categoria de Despesa";"Categoria de Despesa";"Código Grupo de Despesa";'
    '"Grupo de Despesa";"Código Modalidade de Aplicação";"Modalidade de Aplicação";"Código Elemento de Despesa";'
    '"Elemento de Despesa";"Código SubElemento de Despesa";"SubElemento de Despesa";"Descrição";"Quantidade";'
    '"Valor Unitário";"Valor Total";"Sequencial";"Valor Atual"\n'
    f'"1";"{UG}152612025NE000011";"3";"Desp Correntes";"3";"ODC";"90";"Aplic Diretas";"30";"Mat Consumo";"16";'
    '"MATERIAL DE EXPEDIENTE";"PAPEL A4 75G BRANCO RESMA 500 FOLHAS";"500";"25,00";"12500,00";"1";"12500,00"\n'
)
LIQ = (
    '"Código Liquidação";"Código Liquidação Resumido";"Data Emissão";"Código Tipo Documento";"Tipo Documento";'
    '"Código Órgão Superior";"Órgão Superior";"Código Órgão";"Órgão";"Código Unidade Gestora";"Unidade Gestora";'
    '"Código Gestão";"Gestão";"Código Favorecido";"Favorecido";"Observação";"Código Categoria de Despesa";'
    '"Categoria de Despesa";"Código Grupo de Despesa";"Grupo de Despesa";"Código Modalidade de Aplicação";'
    '"Modalidade de Aplicação";"Código Elemento de Despesa";"Elemento de Despesa";"Código Plano Orçamentário";'
    '"Plano Orçamentário";"Código Programa Governo";"Nome Programa Governo"\n'
    f'"{UG}152612025NS000100";"2025NS000100";"15/01/2025";"NS";"Nota de Sistema";"26000";"MEC";"26240";"UFPB";'
    f'"{UG}";"UFPB";"15231";"UFPB";"09095183000140";"ENERGISA PARAIBA";"Fatura dez/2024";"3";"DC";"3";"ODC";"90";"AD";'
    '"39";"OSTPJ";"0000";"PO";"";""\n'
    f'"{UG}152612025NS000101";"2025NS000101";"15/01/2025";"NS";"Nota de Sistema";"26000";"MEC";"26240";"UFPB";'
    f'"{UG}";"UFPB";"15231";"UFPB";"***.123.456-**";"FULANO";"Diarias do Fulano";"3";"DC";"3";"ODC";"90";"AD";'
    '"14";"Diarias";"0000";"PO";"";""\n'
)
LIQ_IMP = (
    '"Código Liquidação";"Código Empenho";"Código Natureza Despesa Completa";"Subitem";"Valor Liquidado (R$)";'
    '"Valor Restos a Pagar Inscritos (R$)";"Valor Restos a Pagar Cancelado (R$)";"Valor Restos a Pagar Pagos (R$)"\n'
    f'"{UG}152612025NS000100";"{UG}152612024NE000900";"33903943";"43";"75300,10";"0,00";"0,00";"0,00"\n'
    f'"{UG}152612025NS000101";"{UG}152612025NE000050";"33901414";"14";"1020,00";"0,00";"0,00";"0,00"\n'
    f'"{UG}152612025NS000102";"{UG}152612025NE000060";"31901101";"01";"999999,00";"0,00";"0,00";"0,00"\n'
)
PAG = (
    '"Código Pagamento";"Código Pagamento Resumido";"Data Emissão";"Código Tipo Documento";"Tipo Documento";'
    '"Código Unidade Gestora";"Unidade Gestora";"Código Favorecido";"Favorecido";"Observação"\n'
    f'"{UG}152612025OB000200";"2025OB000200";"15/01/2025";"OB";"Ordem Bancária";"{UG}";"UFPB";"09095183000140";'
    '"ENERGISA PARAIBA";"Pgto fatura"\n'
)
PAG_IMP = (
    '"Código Pagamento";"Código Empenho";"Código Natureza Despesa Completa";"Subitem";"Valor Pago (R$)";'
    '"Valor Restos a Pagar Inscritos (R$)";"Valor Restos a Pagar Cancelado (R$)";"Valor Restos a Pagar Pagos (R$)"\n'
    f'"{UG}152612025OB000200";"{UG}152612024NE000900";"33903943";"43";"0,00";"0,00";"0,00";"70000,00"\n'
)


def _zip() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for sufixo, txt in {
            "Despesas_Empenho": EMPENHO, "Despesas_ItemEmpenho": ITEM, "Despesas_Liquidacao": LIQ,
            "Despesas_Liquidacao_EmpenhosImpactados": LIQ_IMP, "Despesas_Pagamento": PAG,
            "Despesas_Pagamento_EmpenhosImpactados": PAG_IMP, "Despesas_Pagamento_ListaBancos": "x\n",
        }.items():
            z.writestr(f"{DIA}_{sufixo}.csv", txt.encode("latin-1"))
    return buf.getvalue()


@pytest.fixture
def cache(tmp_path, monkeypatch):
    from despesas.portal_bulk import _filtrar_zip

    monkeypatch.setattr(config, "RAW_DIR", tmp_path / "raw")
    monkeypatch.setattr(config, "UGS", [UG])
    bruto = _filtrar_zip(_zip())
    write_json(raw_path("portal_bulk", "2025", "2025-01-15.json"), {"ugs": [UG], "dados": bruto})
    return bruto


def test_filtro_so_ufpb(cache):
    assert [e["codigo_empenho"][:6] for e in cache["empenho"]] == [UG]
    assert len(cache["liquidacao_impactados"]) == 3  # filtra pelo documento, nao pelo empenho


def test_dia_bulk_normalizado(cache):
    from despesas.load_despesas import COL_FATO, COL_ITENS, extract_transform
    from despesas.portal_bulk import PortalBulk

    frames, info = extract_transform(Janela.de_args("2025-01", "2025-01"), PortalBulk(offline=True), None)
    assert info["fontes"] == {"arquivo": 1, "api": 0, "sem dados": 30}

    fato = frames[COL_FATO].set_index(["fase", "documento"])
    energia = fato.loc[("liquidacao", f"{UG}152612025NS000100")]
    assert (energia["natureza"], energia["tema_codigo"]) == ("33903943", "energia")
    assert energia["valor"] == pytest.approx(75300.10)
    assert energia["favorecido_nome"] == "ENERGISA PARAIBA"

    diaria = fato.loc[("liquidacao", f"{UG}152612025NS000101")]
    assert diaria["tema_codigo"] == "deslocamento"
    assert diaria["favorecido_tipo"] == "PF" and diaria[["favorecido_codigo", "favorecido_nome", "observacao"]].isna().all()

    assert f"{UG}152612025NS000102" not in fato.index.get_level_values(1)  # folha (3190.11) fora

    pago = fato.loc[("pagamento", f"{UG}152612025OB000200")]
    assert pago["valor"] == pytest.approx(70000.0)  # restos a pagar pagos entram no "pago"

    item = frames[COL_ITENS].iloc[0]
    assert item["natureza"] == "33903016"
    assert item["regras_texto"] == ["papel_a4"]
    assert (item["quantidade"], item["valor_unitario"]) == (500, 25)


def test_mes_incompleto_nao_e_gravado(cache, tmp_path, monkeypatch, capsys):
    from despesas import load_despesas

    monkeypatch.setattr(config, "PROCESSED_DIR", tmp_path / "processed")
    monkeypatch.setattr(config, "PORTAL_API_KEY", "")
    load_despesas.run(inicio="2025-01", fim="2025-01", offline=True, dry_run=True)
    assert "meses incompletos nao serao gravados: 2025-01" in capsys.readouterr().out


def test_validacao_tesouro_gerencial(cache, tmp_path, monkeypatch, capsys):
    from despesas import load_despesas
    from despesas.load_despesas import COL_FATO, extract_transform
    from despesas.portal_bulk import PortalBulk

    tg = tmp_path / "tg.csv"
    # exportacao com todas as naturezas: a 3.1.90.11.01 (folha, fora do mapeamento) e ignorada
    tg.write_text(
        "ano;natureza;liquidado;pago\n"
        "2025;3.3.90.39.43;75.300,10;70.000,00\n"
        "2025;3.3.90.14.14;999,00;0\n"
        "2025;3.1.90.11.01;5.000.000,00;5.000.000,00\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(load_despesas, "VALIDACAO_TG", tg)
    frames, _ = extract_transform(Janela.de_args("2025-01", "2025-01"), PortalBulk(offline=True), None)
    load_despesas._validar_tesouro(frames[COL_FATO])
    out = capsys.readouterr().out
    assert "2025|33903943: 75,300.10 (OK" in out
    assert "2025|33901414: 1020 (referencia era 999 - divergencia" in out
    assert "31901101" not in out
    assert "=== Totais de carga - pago x Tesouro Gerencial" in out


def test_cache_de_outras_ugs_e_rebaixado(cache, monkeypatch):
    from datetime import date

    from despesas.portal_bulk import PortalBulk

    assert PortalBulk(offline=True).dia(date(2025, 1, 15)) is not None
    monkeypatch.setattr(config, "UGS", [UG, "153073"])  # UG nova: o cache nao serve mais
    assert PortalBulk(offline=True).dia(date(2025, 1, 15)) is None


def test_queda_de_rede_nao_derruba_a_carga(tmp_path, monkeypatch):
    from datetime import date

    import requests

    from despesas import portal_bulk

    monkeypatch.setattr(config, "RAW_DIR", tmp_path / "raw")
    monkeypatch.setattr(config, "PORTAL_BULK_TENTATIVAS", 1)
    monkeypatch.setattr(config, "PORTAL_BULK_PAUSA_S", 0)
    bulk = portal_bulk.PortalBulk()

    def sem_rede(*_a, **_k):
        raise RuntimeError("Falha apos 5 tentativas") from requests.ConnectionError("getaddrinfo failed")

    monkeypatch.setattr(bulk.client, "get", sem_rede)
    assert bulk.dia(date(2024, 1, 10)) is None
    assert bulk.bloqueado  # para de tentar, segue com o cache
    assert bulk.dia(date(2024, 1, 11)) is None


def test_validacao_mensal(cache, tmp_path, monkeypatch, capsys):
    from despesas import load_despesas
    from despesas.load_despesas import COL_FATO, extract_transform
    from despesas.portal_bulk import PortalBulk

    tg = tmp_path / "tesouro_gerencial_liquidado.csv"
    tg.write_text("ano;natureza;liquidado;pago\n", encoding="utf-8")
    (tmp_path / "tesouro_gerencial_mensal.csv").write_text(
        "periodo;natureza;liquidado;pago\n2025-01;33903943;75300,10;60000,00\n", encoding="utf-8"
    )
    monkeypatch.setattr(load_despesas, "VALIDACAO_TG", tg)
    frames, _ = extract_transform(Janela.de_args("2025-01", "2025-01"), PortalBulk(offline=True), None)
    load_despesas._validar_tesouro_mensal(frames[COL_FATO])
    out = capsys.readouterr().out
    assert "liquidado x Tesouro Gerencial, mes a mes: 1 de 2" in out  # energia bate; diaria so no ETL
    assert "2025-01 33903943: ETL 70,000.00 x TG 60,000.00 (dif +10,000.00)" in out


def test_zip_remoto_pausa_no_bloqueio(monkeypatch):
    from common import config, remote_zip

    monkeypatch.setattr(config, "PORTAL_BULK_PAUSA_S", 0)
    monkeypatch.setattr(config, "PORTAL_BULK_TENTATIVAS", 2)

    class Resp:
        def __init__(self, status):
            self.status_code = status

        def raise_for_status(self):
            if self.status_code >= 400:
                raise RuntimeError(self.status_code)

    respostas = iter([Resp(405), Resp(405), Resp(200)])
    assert remote_zip.HttpRangeFile._retry(lambda: next(respostas)).status_code == 200
    respostas = iter([Resp(405)] * 3)
    with pytest.raises(RuntimeError):
        remote_zip.HttpRangeFile._retry(lambda: next(respostas))


def test_itens_com_especie_nao_se_aplica(tmp_path, monkeypatch):
    # nos arquivos reais a especie do empenho vem sempre 'Nao se aplica' (2025):
    # os itens do empenho emitido no dia nao podem ser descartados
    from despesas import portal_bulk
    from despesas.load_despesas import COL_ITENS, extract_transform
    from despesas.portal_bulk import PortalBulk

    real = EMPENHO.replace('"Original"', '"Não se aplica"')
    monkeypatch.setattr(config, "RAW_DIR", tmp_path / "raw")
    monkeypatch.setattr(config, "UGS", [UG])
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for sufixo, txt in {
            "Despesas_Empenho": real, "Despesas_ItemEmpenho": ITEM, "Despesas_Liquidacao": LIQ,
            "Despesas_Liquidacao_EmpenhosImpactados": LIQ_IMP, "Despesas_Pagamento": PAG,
            "Despesas_Pagamento_EmpenhosImpactados": PAG_IMP, "Despesas_Pagamento_ListaBancos": "x\n",
        }.items():
            z.writestr(f"{DIA}_{sufixo}.csv", txt.encode("latin-1"))
    write_json(raw_path("portal_bulk", "2025", "2025-01-15.json"),
               {"ugs": [UG], "dados": portal_bulk._filtrar_zip(buf.getvalue())})
    frames, _ = extract_transform(Janela.de_args("2025-01", "2025-01"), PortalBulk(offline=True), None)
    assert frames[COL_ITENS]["regras_texto"].tolist() == [["papel_a4"]]


def test_arquivo_de_um_dia_recusado_nao_trava_a_carga(tmp_path, monkeypatch):
    # 2022-03-27: o Portal responde 403 so para este arquivo; o dia seguinte sai normal
    from datetime import date

    import requests

    from despesas.portal_bulk import PortalBulk

    monkeypatch.setattr(config, "RAW_DIR", tmp_path / "raw")
    monkeypatch.setattr(config, "PORTAL_BULK_PAUSA_S", 0)
    bulk = PortalBulk()

    def recusa(url, *a, **k):
        resp = requests.Response()
        resp.status_code = 403
        raise requests.HTTPError(response=resp)

    class Vizinho:
        status_code = 206

    monkeypatch.setattr(bulk.client, "get", recusa)
    monkeypatch.setattr(bulk.client.session, "get", lambda *a, **k: Vizinho())
    dados = bulk.dia(date(2022, 3, 27))
    assert dados["pagamento"] == [] and bulk.indisponiveis == [date(2022, 3, 27)]
    assert not bulk.bloqueado
    assert PortalBulk(offline=True).dia(date(2022, 3, 27)) == dados  # marcado no cache
