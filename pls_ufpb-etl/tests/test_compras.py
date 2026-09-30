import io
import zipfile

import pandas as pd

from compras import classificar as c
from compras import load_compras as m
from indicadores import build_indicadores as b

TR = ("UASG 153065 Termo de Referência 41/2024\nSustentabilidade:\n4.1. Além dos critérios de sustentabilidade "
      "eventualmente inseridos na descrição do objeto, devem ser atendidos os seguintes requisitos:\n"
      "4.1.1. A contratada deverá providenciar o recolhimento das lâmpadas fluorescentes para destinação final "
      "ambientalmente adequada.")
ETP = ("UASG 153065 Estudo Técnico Preliminar 7/2024\n14. Possíveis impactos ambientais: uso de produtos "
       "biodegradáveis e logística reversa de embalagens, conforme a Lei 12.305.")
SO_GENERICO = ("UASG 153065 Termo de Referência 3/2025\nA contratada deverá observar, no que couber, os critérios de "
               "sustentabilidade ambiental previstos na Instrução Normativa nº 1, de 19 de janeiro de 2010.")


def test_criterio_concreto_no_tr_e_especifico():
    r = c.classificar([("Edital", [TR, ETP])])
    assert r["nivel_sustentabilidade"] == "especifico"
    assert any("Recolhimento" in x for x in r["criterios"])
    assert r["trechos"]


def test_criterio_so_no_etp_nao_conta():
    r = c.classificar([("Edital", [ETP + " " * 10])])
    assert r["nivel_sustentabilidade"] == "generico"  # a Lei 12.305 no ETP e so mencao
    r = c.classificar([("Estudo Técnico Preliminar", ["Plano de estudo sem cabeçalho: logística reversa de pilhas e baterias."])])
    assert r["nivel_sustentabilidade"] == "nenhum"


def test_mencao_generica_e_sem_texto():
    assert c.classificar([("Termo de Referência", [SO_GENERICO])])["nivel_sustentabilidade"] == "generico"
    assert c.classificar([("Edital", ["  "])])["nivel_sustentabilidade"] == "sem_texto"
    assert c.classificar([("Edital", ["Aquisição de canetas esferográficas azuis conforme especificação técnica do item."])])[
        "nivel_sustentabilidade"] == "nenhum"


def test_marcadores_do_objeto_e_do_documento():
    r = c.classificar([("Edital", ["Será reservado o percentual mínimo de 8% das vagas a mulheres vítimas de violência "
                                   "doméstica, nos termos do Decreto nº 11.430, de 2023."])],
                      objeto="Serviços continuados de limpeza com regime de dedicação exclusiva de mão de obra")
    assert set(r["marcadores"]) == {"mao_obra_exclusiva", "cota_mulheres"}
    assert c.classificar([], "Serviços sem dedicação exclusiva de mão de obra")["marcadores"] == []
    assert c.classificar([], "Contratação de obras ou serviços de engenharia contínuos de agenciamento de passagens")[
        "marcadores"] == []
    assert c.classificar([], "Reforma do bloco B do CCEN")["marcadores"] == ["obra_engenharia"]


def test_paginas_de_zip_com_varios_arquivos():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("a.txt", "primeiro documento")
        z.writestr("b.html", "<p>segundo</p>")
    assert [p.strip() for p in c.paginas(buf.getvalue(), "x.zip")] == ["primeiro documento", "segundo"]


def test_chave_do_controle_pncp():
    assert m._chave("24098477000110-1-000370/2024") == ("24098477000110", 2024, 370)


def test_compras_externas_uma_por_compra():
    regs = [
        {"numeroControlePncpCompra": "24098477000110-1-000001/2025", "dataAssinatura": "2025-02-01"},
        {"numeroControlePncpCompra": "00394502000144-1-007528/2024", "frutoAdesao": False,
         "dataAssinatura": "2025-03-01", "valorGlobal": 100.0, "objetoContrato": "microfone"},
        {"numeroControlePncpCompra": "00394502000144-1-007528/2024", "frutoAdesao": True,
         "dataAssinatura": "2025-04-01", "valorGlobal": 50.0},
        {"numeroControlePncpCompra": None},
    ]
    out = m.compras_externas(regs)
    assert len(out) == 1
    assert out[0]["tipo"] == "Adesão da UFPB a ata de outro órgão" and out[0]["valor"] == 150.0
    assert out[0]["data"] == "2025-03-01"


def test_metricas_de_compras(monkeypatch):
    compras = pd.DataFrame([
        {"periodo": "2025-03", "modalidade": "Pregão - Eletrônico", "nivel_sustentabilidade": "especifico", "valor": 100.0,
         "marcadores": ["mao_obra_exclusiva", "cota_mulheres"], "margem_preferencia": True},
        {"periodo": "2025-03", "modalidade": "Pregão - Eletrônico", "nivel_sustentabilidade": "generico", "valor": 50.0,
         "marcadores": ["mao_obra_exclusiva"], "margem_preferencia": False},
        {"periodo": "2025-04", "modalidade": "Inexigibilidade", "nivel_sustentabilidade": "nao_lido", "valor": 10.0,
         "marcadores": [], "margem_preferencia": False},
    ])
    comp = pd.DataFrame([{"tipo": "IRP da UFPB com participante externo", "periodo": "2025-05"}])
    tabelas = {"pls_compras": compras, "pls_compras_compartilhadas": comp}
    monkeypatch.setattr(b, "load_processed", lambda nome: tabelas.get(nome, pd.DataFrame()))
    df = b._compras()
    q = df[df["metrica"] == "contratacoes_pncp"].set_index("subtema")["valor"].to_dict()
    assert q == {"Licitação · critério específico": 1, "Licitação · só menção genérica": 1,
                 "Inexigibilidade · documentos não lidos": 1}
    e = df[df["metrica"] == "editais_marcadores"].set_index("subtema")["valor"].to_dict()
    assert e["Mão de obra exclusiva · com cota para mulheres"] == 1
    assert e["Mão de obra exclusiva · sem cota para mulheres"] == 1
    assert e["Licitações · com margem de preferência"] == 1
    assert df[df["metrica"] == "compras_compartilhadas"]["valor"].sum() == 1


def test_clausula_de_preferencia_nao_e_criterio_especifico():
    pref = ("UASG 153065 Termo de Referência 9/2024\n4.1.2. Que os bens sejam, preferencialmente, acondicionados em "
            "embalagem individual adequada, que utilize materiais recicláveis; 4.1.3. Que os bens não contenham "
            "substâncias perigosas.")
    r = c.classificar([("Termo de Referência", [pref])])
    assert r["nivel_sustentabilidade"] == "preferencial"
    assert r["criterios"] == [] and r["preferenciais"]
    obrig = pref + " 4.1.4. Os bens deverão ser constituídos por material reciclado, conforme ABNT NBR 15448."
    r = c.classificar([("Termo de Referência", [obrig])])
    assert r["nivel_sustentabilidade"] == "especifico" and r["preferenciais"] == []


def test_reciclado_negado_nao_e_criterio():
    from compras.classificar import classificar
    docs = [("Termo de Referência", ["UASG 153065 Termo de Referencia 1/2025 " + "x" * 40 +
                                     " A CONTRATADA FORNECERA TOALHAS DE PAPEL NAO RECICLADO NOS SANITARIOS."])]
    assert classificar(docs)["nivel_sustentabilidade"] != "especifico"
