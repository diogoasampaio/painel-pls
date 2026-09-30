"""Validacao dos 15 indicadores do nucleo do PLS: dado captado, construcao, o que conferir e melhorias.

    python relatorios/gerar_validacao_nucleo.py [--saida DIR]

Gera validacao_indicadores_pls.docx (Word, paisagem) e .html. Complementa as
fichas tecnicas (gerar_fichas_nucleo.py): em vez de repetir a construcao em
detalhe, mede o que cada base realmente trouxe (documentos lidos, meses,
unidades, lacunas), aponta o que a Comissao e os setores precisam conferir e
separa as melhorias em tres tipos:

  automatizavel  o painel faz sozinho, so programacao
  com_acesso     automatico depois de um acesso ou extracao que depende de outro setor
  setor          depende de informacao, decisao ou rotina de um setor

Numeros de captacao: calculados dos parquets de data/processed a cada geracao.
Textos editaveis pela Comissao: ref/validacao_nucleo.csv (confianca, motivo, o
que verificar, quem) e ref/validacao_melhorias.csv (melhoria, tipo, como, quem,
prioridade).
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

import pandas as pd

ETL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ETL))
from common import config  # noqa: E402
from common.comunidade import ufpb as comunidade_ufpb  # noqa: E402
from common.storage import load_processed  # noqa: E402
from relatorios.blocos import Doc, docx_doc, html_doc, num  # noqa: E402
from relatorios.gerar_fichas_nucleo import Dados  # noqa: E402

ANOS = [2023, 2024, 2025, 2026]
ANO_FECHADO = 2025
TIPO = {"automatizavel": "Automatizável pelo painel", "com_acesso": "Automatizável com acesso a dado",
        "setor": "Depende do setor ou da Comissão"}
ORDEM_PRIORIDADE = {"Alta": 0, "Média": 1, "Baixa": 2}
MESES_LONGOS = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro",
                "outubro", "novembro", "dezembro"]
MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]


def n(v, casas=0) -> str:
    return "—" if v is None or v != v else num(round(float(v), casas))


def faltando(periodos: set[str], ano: int) -> str:
    fora = [MESES[m - 1] for m in range(1, 13) if f"{ano}-{m:02d}" not in periodos]
    return ", ".join(fora) if fora else "—"


# ------------------------------------------------------------------ bases

class Bases:
    def __init__(self):
        self.fat = load_processed("pls_faturas")
        self.fat = self.fat[self.fat["status"] == "ok"].assign(ano_ref=lambda d: d["periodo"].str[:4].astype(int))
        self.desp = load_processed("pls_despesas")
        pg = self.desp[self.desp["fase"] == "pagamento"]
        self.pag = pg.assign(v=pg["valor_pago"].fillna(0) + pg["valor_rp_pago"].fillna(0))
        self.ind = load_processed("pls_indicadores")
        self.itens = load_processed("pls_itens_empenho")
        self.compras = load_processed("pls_compras")
        self.compart = load_processed("pls_compras_compartilhadas")
        self.pj = load_processed("pls_pagamentos_pj")
        self.evg = load_processed("pls_evg")
        self.trechos = load_processed("pls_trechos")
        self.acoes = load_processed("pls_acoes")
        self.area = pd.read_csv(config.REF_DIR / "area_construida.csv", sep=";")
        self.com = comunidade_ufpb()

    # faturas: documentos, unidades e meses por ano de referencia
    def faturas(self, tipo: str, qtd: str, unid: str, chave: str = "uc") -> tuple[list[str], list[list]]:
        f = self.fat[self.fat["tipo"] == tipo]
        cab = ["Ano", "Processos de pagamento", "Linhas lidas", "Unidades" if chave == "uc" else "Placas",
               "Meses com dado", "Meses faltando", f"Total ({unid})"]
        linhas = []
        for a in ANOS:
            s = f[f["ano_ref"] == a]
            if s.empty:
                continue
            per = set(s["periodo"])
            linhas.append([str(a), n(s["processo"].nunique()), n(len(s)), n(s[chave].nunique()), n(len(per)),
                           faltando(per, a) if a < date.today().year else f"até {MESES[max(int(p[5:]) for p in per) - 1]}",
                           n(s[qtd].sum())])
        return cab, linhas

    def pagamentos(self, subtemas: list[str] | None = None, acao: str | None = None) -> tuple[list[str], list[list]]:
        p = self.pag
        if subtemas:
            p = p[p["subtema"].isin(subtemas)]
        if acao:
            p = p[p["acao"].astype(str) == acao]
        cab = ["Ano", "Pagamentos", "Favorecidos", "Meses com pagamento", "Pago (R$ correntes)"]
        linhas = [[str(a), n(len(s)), n(s["favorecido_codigo"].nunique()), n(s["mes"].nunique()), n(s["v"].sum())]
                  for a in ANOS if not (s := p[p["ano"] == a]).empty]
        return cab, linhas

    def metrica(self, metrica: str, ano: int) -> pd.Series:
        m = self.ind[(self.ind["metrica"] == metrica) & (self.ind["ano"] == ano)]
        return m.groupby("subtema")["valor_nominal"].sum()


# ------------------------------------------------------------------ captacao por indicador

def captacao(b: Bases, codigo: str) -> tuple[str, list[str], list[list], str]:
    """(texto do que foi captado, cabecalho, linhas, nota)"""
    area = b.area["area_m2"].sum()
    if codigo in ("N01", "N02"):
        tipo, qtd, unid = ("energia", "kwh", "kWh") if codigo == "N01" else ("agua", "m3", "m³")
        cab, linhas = b.faturas(tipo, qtd, unid)
        if codigo == "N01":
            txt = (f"Faturas agrupadas da Energisa anexadas aos processos de pagamento no SIPAC, lidas uma a uma. Cada "
                   f"linha é uma unidade consumidora em um mês, com kWh medido, kWh faturado e demanda. Denominador: "
                   f"área construída de {num(area)} m² (ref/area_construida.csv), a mesma para todos os anos.")
            return txt, cab, linhas, ("Em 2026 as mesmas 23 unidades aparecem com dois códigos: a Energisa mudou o formato "
                                      "do código a partir de março, por isso a contagem de unidades dobra no ano.")
        com = b.com.reindex(ANOS)
        cab2 = cab + ["Comunidade (pessoas)", "Fonte da comunidade"]
        linhas = [l + [n(com.loc[int(l[0]), "comunidade"]) if int(l[0]) in com.dropna().index else "usa o último ano",
                       com.loc[int(l[0]), "fonte"] if int(l[0]) in com.dropna().index else ""] for l in linhas]
        txt = ("Faturas agrupadas da CAGEPA anexadas aos processos de pagamento no SIPAC. Cada linha é uma ligação em um "
               "mês, com m³ medido e faturado (vale o medido, ou o faturado quando houve troca de hidrômetro). "
               "Denominador: contagem da comunidade acadêmica da UFPB (discentes, docentes, técnicos e terceirizados).")
        return txt, cab2, linhas, ""
    if codigo == "N03":
        cab = ["Ano", "Frota (L)", "Energia da rede (kWh)", "Trechos aéreos", "Distância aérea (km)", "Escopo 1 (t)",
               "Escopo 2 (t)", "Escopo 3 (t)", "Total (t CO₂e)"]
        linhas = []
        for a in ANOS:
            g = b.metrica("emissoes_kgco2e", a) / 1000
            if g.empty:
                continue
            ta = b.trechos[(b.trechos["ano"] == a) & b.trechos["meio_transporte"].str.contains("A[eé]reo", case=False, na=False)]
            e1 = g[g.index.str.startswith("Escopo 1")].sum()
            linhas.append([str(a), n(b.fat[(b.fat.tipo == "combustivel") & (b.fat.ano_ref == a)]["litros"].sum()),
                           n(b.fat[(b.fat.tipo == "energia") & (b.fat.ano_ref == a)]["kwh"].sum()), n(len(ta)),
                           n(ta["distancia_km"].sum()), n(e1, 1), n(g[g.index.str.startswith("Escopo 2")].sum(), 1),
                           n(g[g.index.str.startswith("Escopo 3")].sum(), 1), n(g.sum(), 1)])
        txt = ("Três bases físicas: litros abastecidos pela frota (relatório da gerenciadora nos processos), kWh consumido "
               "da rede (faturas da Energisa, com o fator mensal do SIN publicado pelo MCTI) e trechos aéreos das viagens "
               "a serviço (Portal da Transparência, distância entre aeroportos). Fatores em ref/fatores_gee.csv.")
        return txt, cab, linhas, "Escopo 3 só com viagens aéreas: viagens terrestres, resíduos e gases refrigerantes ainda fora."
    if codigo == "N04":
        cab, linhas = b.faturas("residuos", "kg", "kg")
        txt = ("Relatórios mensais de fiscalização da coleta de resíduos de serviços de saúde (grupos A, B e E), anexados "
               "aos processos de pagamento da empresa contratada. Recicláveis ainda não entram.")
        return txt, cab, linhas, ""
    if codigo in ("N05", "N06"):
        subs = (["Fatura de energia elétrica", "Fatura de água e esgoto", "Limpeza e conservação", "Manutenção predial"]
                if codigo == "N05" else ["Manutenção predial"])
        cab, linhas = b.pagamentos(subs)
        txt = (f"Pagamentos (inclusive restos a pagar) dos arquivos diários de despesas do Portal da Transparência nas "
               f"naturezas de {', '.join(s.lower() for s in subs)}, corrigidos pelo IPCA. Denominador: área construída de "
               f"{num(area)} m², a mesma para todos os anos.")
        return txt, cab, linhas, "O mês é o do pagamento, não o do serviço."
    if codigo == "N07":
        cab = ["Ano", "Diesel S10 (L)", "Diesel comum (L)", "Gasolina (L)", "Etanol (L)", "Litros sem placa", "Postos", "Menos poluente"]
        linhas = []
        for a in ANOS:
            s = b.metrica("consumo_litros", a)
            if s.empty:
                continue
            f = b.fat[(b.fat.tipo == "combustivel") & (b.fat.ano_ref == a)]
            menos = s.get("Frota - diesel S10", 0) + s.get("Frota - etanol", 0)
            linhas.append([str(a), n(s.get("Frota - diesel S10")), n(s.get("Frota - diesel comum")), n(s.get("Frota - gasolina")),
                           n(s.get("Frota - etanol")), n(f[f["placa"].isna()]["litros"].sum()), n(f["cnpj_posto"].nunique()),
                           f"{n(100 * menos / s.sum(), 1)}%"])
        txt = ("Relatório de abastecimentos da gerenciadora de frota anexado ao processo de pagamento mensal: cada linha é um "
               "abastecimento, com placa, combustível, litros e posto. O tipo do diesel sai do texto do relatório.")
        return txt, cab, linhas, "Litros sem placa: meses em que o processo trouxe só a nota fiscal."
    if codigo == "N09":
        cab = ["Ano", "Itens de material de consumo empenhados", "Itens marcados como sustentáveis", "Com atributo (R$)",
               "Demais itens (R$)", "Participação"]
        linhas = []
        for a in ANOS:
            it = b.itens[(b.itens["ano"] == a) & b.itens["natureza"].astype(str).str.startswith("339030")]
            s = b.metrica("empenhado_material_consumo", a)
            if s.empty:
                continue
            marc = it["regras_texto"].astype(str).str.contains("item_sustentavel|papel|toner|led|fotovolt|residuo", regex=True)
            com, dem = s.get("Com atributo sustentável", 0), s.get("Demais itens", 0)
            linhas.append([str(a), n(len(it)), n(marc.sum()), n(com), n(dem), f"{n(100 * com / (com + dem), 2)}%"])
        txt = ("Itens das notas de empenho de material de consumo (3.3.90.30) nos arquivos diários do Portal. Um item conta "
               "como sustentável quando a descrição casa uma regra de texto de ref/regras_texto_pls.csv (reciclado, "
               "biodegradável, refil, certificação, LED...).")
        return txt, cab, linhas, ""
    if codigo == "N10":
        cab = ["Ano", "Contratações publicadas", "Licitações e dispensas lidas", "Critério específico", "Só preferência",
               "Só menção genérica", "Sem critério", "Sem documento legível"]
        linhas = []
        for a in ANOS:
            c = b.compras[b.compras["ano"] == a]
            if c.empty:
                continue
            nv = c["nivel_sustentabilidade"].value_counts()
            linhas.append([str(a), n(len(c)), n((c["leitura"] == "lido").sum()), n(nv.get("especifico")), n(nv.get("preferencial")),
                           n(nv.get("generico")), n(nv.get("nenhum")), n(nv.get("sem_documento", 0) + nv.get("sem_texto", 0))])
        txt = ("Contratações da UFPB publicadas no PNCP. Nas licitações e dispensas, o painel baixa o edital e o termo de "
               "referência e procura critérios de sustentabilidade (ref/criterios_editais.csv). Inexigibilidades ficam fora.")
        return txt, cab, linhas, "Contratações publicadas inclui as inexigibilidades, que não são lidas."
    if codigo == "N11":
        t = b.compart.groupby(["ano", "tipo"]).size().unstack(fill_value=0)
        cab = ["Ano", *t.columns, "Total"]
        linhas = [[str(a), *[n(v) for v in t.loc[a]], n(t.loc[a].sum())] for a in t.index]
        txt = ("Atas de registro de preços e compras publicadas no PNCP e no Compras.gov.br: IRPs da UFPB com participante "
               "externo, adesões de outros órgãos às atas da UFPB e participações da UFPB em compras de outros órgãos.")
        return txt, cab, linhas, ""
    if codigo == "N12":
        cab = ["Ano", "CNPJs pagos", "ME/EPP (R$ mi)", "Demais portes da PB (R$ mi)", "Demais portes de outros estados (R$ mi)",
               "Instituição financeira, fora (R$ mi)", "Sem cadastro (R$ mi)"]
        linhas = []
        for a in ANOS:
            p = b.pj[b.pj["ano"] == a]
            if p.empty:
                continue
            s = p.groupby("subtema")["valor"].sum() / 1e6
            me = s[s.index.str.startswith("ME/EPP")].sum()
            linhas.append([str(a), n(p["cnpj"].nunique()), n(me, 1), n(s.get("Demais portes da Paraíba"), 1),
                           n(s.get("Demais portes de outros estados"), 1), n(s[s.index.str.startswith("Instituição")].sum(), 1),
                           n(s.get("Sem cadastro na Receita", 0), 1)])
        txt = ("Pagamentos a pessoas jurídicas nas naturezas de contratação (Portal), casados pelo CNPJ com o cadastro aberto "
               "da Receita Federal (porte, UF da sede, Simples e MEI).")
        return txt, cab, linhas, "O porte é o do cadastro atual, não o da data do pagamento."
    if codigo == "N13":
        cab = ["Ano", "Matrículas (UFPB declarada)", "Pessoas distintas", "Cursos concluídos", "Concluíram curso de sustentabilidade",
               "Servidores (denominador)", "Resultado"]
        linhas = []
        for a in ANOS:
            e = b.evg[b.evg["ano"] == a]
            if e.empty:
                continue
            sust = e[e["sustentabilidade"] & e["concluida"]]["pessoa"].nunique()
            srv = b.com["servidores"][b.com.index <= a].iloc[-1] if (b.com.index <= a).any() else None
            linhas.append([str(a), n(len(e)), n(e["pessoa"].nunique()), n(e["concluida"].sum()), n(sust), n(srv),
                           f"{n(100 * sust / srv, 2)}%" if srv else "—"])
        txt = ("Arquivos bimestrais da Escola Virtual de Governo (ENAP) no dados.gov.br, só as matrículas de quem declara a "
               "UFPB, sem dado pessoal (código anonimizado). Curso de sustentabilidade pelo nome (ref/evg_sustentabilidade.csv).")
        return txt, cab, linhas, "Cursos fora da EVG e quem não declara a UFPB ficam fora: o dado exato está no SIGRH."
    if codigo == "N14":
        cab, linhas = b.pagamentos(acao="4572")
        a = b.pag[(b.pag["acao"].astype(str) == "4572") & (b.pag["ano"] == ANO_FECHADO)]
        top = a.groupby(a["natureza"].astype(str).str[:6])["v"].sum().sort_values(ascending=False).head(4)
        nomes = {"339020": "auxílio a pesquisadores", "339036": "serviços de pessoa física", "449052": "equipamentos",
                 "339039": "serviços de pessoa jurídica", "339014": "diárias", "339033": "passagens"}
        txt = ("Todos os pagamentos cujo empenho é da ação orçamentária 4572 (Capacitação de servidores), por qualquer "
               "natureza de despesa, nos arquivos diários do Portal. Em " + str(ANO_FECHADO) + ", as maiores naturezas: "
               + "; ".join(f"{nomes.get(k, k)} (R$ {num(v)})" for k, v in top.items()) + ".")
        return txt, cab, linhas, "Valores em R$ correntes; o indicador usa R$ corrigidos pelo IPCA."
    if codigo == "N15":
        a = b.acoes
        sit = a["situacao"].value_counts()
        rot = {"sem_informacao": "Sem informação", "vencida_sem_informacao": "Prazo vencido sem informação", "em_dia": "Em dia",
               "concluida": "Concluída", "atrasada": "Atrasada", "em_andamento": "Em andamento", "a_iniciar": "A iniciar"}
        cab = ["Situação na data de referência", "Ações"]
        linhas = [[rot.get(k, k), n(v)] for k, v in sit.items()] + [["Verificadas pelo próprio painel", n(a["verificada_painel"].sum())]]
        txt = (f"Plano de ações do PLS ({len(a)} ações e rotinas) e o formulário de acompanhamento semestral dos "
               f"responsáveis, na data de referência {a['data_referencia'].iloc[0]}.")
        return txt, cab, linhas, ""
    if codigo == "N08":
        return ("Nenhum dado captado: a geração das usinas fotovoltaicas não passa pelo medidor da Energisa e ainda não foi "
                "informada pela SINFRA."), [], [], ""
    return "", [], [], ""


CONSTRUCAO = {
    "N01": ["Somar o kWh medido de todas as unidades consumidoras por mês de referência da fatura.",
            "Somar os 12 meses do ano e dividir pela área construída total."],
    "N02": ["Somar o m³ medido (ou faturado, com troca de hidrômetro) das ligações por mês de referência.",
            "Somar os 12 meses e dividir pela comunidade acadêmica do ano (ou do último ano disponível)."],
    "N03": ["Frota: litros × fator do combustível, descontada a mistura obrigatória de biocombustível (escopo 1).",
            "Energia: kWh da rede × fator mensal do SIN do MCTI (escopo 2).",
            "Viagens aéreas: distância de cada trecho × fator por faixa de distância (escopo 3). Soma em toneladas."],
    "N04": ["Somar o peso (kg) dos relatórios mensais de fiscalização por mês de referência."],
    "N05": ["Somar o pago em energia, água, limpeza e manutenção predial no ano, corrigido pelo IPCA.",
            "Dividir pela área construída total."],
    "N06": ["Somar o pago em manutenção predial no ano, corrigido pelo IPCA, e dividir pela área construída."],
    "N07": ["Somar os litros de etanol e diesel S10 e dividir pelo total de litros do ano × 100."],
    "N08": ["Geração das usinas ÷ (geração + kWh consumido da rede) × 100, quando a SINFRA informar a geração."],
    "N09": ["Somar o valor empenhado dos itens com atributo sustentável e dividir pelo total empenhado em material de consumo × 100."],
    "N10": ["Classificar cada licitação e dispensa pelo nível de critério encontrado no edital ou termo de referência.",
            "Contratações com critério específico ÷ contratações lidas × 100 (sem as de documento ilegível)."],
    "N11": ["Contar cada compra compartilhada uma vez no ano (IRP com participante externo, adesão externa, participação da UFPB)."],
    "N12": ["Pago a ME/EPP, agricultura familiar e demais fornecedores da Paraíba ÷ pago a pessoas jurídicas × 100, sem instituições financeiras."],
    "N13": ["Contar as pessoas distintas que concluíram curso de sustentabilidade no ano e dividir pelos docentes + técnicos × 100."],
    "N14": ["Somar o pago em todas as naturezas da ação 4572 no ano, corrigido pelo IPCA."],
    "N15": ["Classificar cada ação pela situação na data de referência.",
            "Ações concluídas, em dia ou em andamento com evidência ÷ ações exigíveis × 100."],
}


# ------------------------------------------------------------------ achados da verificacao

def achados(b: Bases) -> list[str]:
    out = []
    e = b.fat[b.fat["tipo"] == "energia"]
    for a in sorted(e["ano_ref"].unique()):
        s = e[e["ano_ref"] == a]
        por_mes = s.groupby("periodo")["uc"].nunique().max()
        if s["uc"].nunique() > por_mes:
            ini = s[s["uc"].str.len() > 8]["periodo"].min()
            novos = f"{MESES_LONGOS[int(ini[5:]) - 1]} de {ini[:4]}"
            out.append(f"**Energia (N01, N03, N05):** em {a} a Energisa passou a usar um código novo de unidade consumidora "
                       f"a partir de {novos}. O total do mês está certo ({por_mes} unidades), mas a série por unidade e o alerta de "
                       f"variação acima de 50% perdem a ligação entre o código antigo e o novo.")
    for tipo, nome in (("energia", "Energia"), ("agua", "Água"), ("residuos", "Resíduos"), ("combustivel", "Combustível")):
        f = b.fat[b.fat["tipo"] == tipo]
        for a in range(2023, ANO_FECHADO + 1):
            falta = faltando(set(f[f["ano_ref"] == a]["periodo"]), a)
            if falta != "—":
                out.append(f"**{nome}:** {a} sem dado em {falta}, por isso o ano fica incompleto e não é avaliado contra a meta.")
    c = b.fat[b.fat["tipo"] == "combustivel"]
    sem = c[c["placa"].isna()].groupby("ano_ref")["litros"].sum()
    if not sem.empty:
        out.append("**Combustível (N03, N07):** litros sem placa (processo só com a nota fiscal): "
                   + "; ".join(f"{a}: {num(v)} L" for a, v in sem.items()) + ". Esses litros entram todos no Campus I.")
    ano = b.compras[b.compras["ano"] == ANO_FECHADO]
    ilegivel = ano["nivel_sustentabilidade"].isin(["sem_documento", "sem_texto"]).sum()
    out.append(f"**Contratações (N10):** em {ANO_FECHADO}, {ilegivel} licitações ou dispensas sem edital ou termo de referência "
               f"legível e {int((ano['leitura'] == 'nao_lido').sum())} inexigibilidades fora do universo.")
    e = b.evg[(b.evg["ano"] == ANO_FECHADO) & b.evg["sustentabilidade"] & b.evg["concluida"]]
    out.append(f"**Capacitação (N13):** o resultado de {ANO_FECHADO} vem de {e['pessoa'].nunique()} pessoas. Com base tão pequena, "
               f"poucas pessoas mudam o indicador de forma grande.")
    a = b.acoes
    out.append(f"**Plano de ações (N15):** {int(a['situacao'].isin(['sem_informacao', 'vencida_sem_informacao']).sum())} de {len(a)} "
               f"ações sem registro no ciclo.")
    out.append(f"**Área construída (N01, N05, N06):** {num(b.area['area_m2'].sum())} m² em {len(b.area)} unidades, em números "
               f"redondos e com a mesma área para todos os anos.")
    return out


# ------------------------------------------------------------------ documento

def montar() -> tuple[Doc, dict]:
    d = Dados()
    b = Bases()
    val = pd.read_csv(config.REF_DIR / "validacao_nucleo.csv", sep=";", dtype=str, keep_default_na=False)
    mel = pd.read_csv(config.REF_DIR / "validacao_melhorias.csv", sep=";", dtype=str, keep_default_na=False)
    mel["o"] = mel["prioridade"].map(ORDEM_PRIORIDADE)
    # a 1a linha de cada indicador traz confianca e motivo; as demais, so conferencias
    conf = val[val["confianca"] != ""].drop_duplicates("codigo").set_index("codigo")
    doc = Doc()

    doc.h1("Como usar este documento")
    doc.p("Este documento serve para validar os 15 indicadores do núcleo do PLS antes de levá-los ao índice e às metas. "
          "Para cada indicador ele mostra o dado que o painel realmente captou (documentos lidos, meses, unidades, lacunas), "
          "como o valor foi construído, o que a Comissão e os setores precisam conferir e as melhorias, separadas pelo que "
          "pode ser automatizado.")
    doc.p("A construção em detalhe (variáveis, endereços das fontes, regras, exemplo rastreado) está nas fichas técnicas; "
          "aqui o foco é a qualidade do dado e o caminho para melhorá-lo.")
    doc.lista([f"**{TIPO['automatizavel']}:** o painel faz sozinho, com programação, sem pedir nada a outro setor.",
               f"**{TIPO['com_acesso']}:** fica automático depois de um acesso ou de uma extração periódica que depende de "
               "outro setor (STI, SINFRA, PROGEP, fornecedor).",
               f"**{TIPO['setor']}:** depende de informação, decisão ou rotina de um setor."])
    cont = mel["tipo"].value_counts()
    doc.kpis([(str(len(d.nucleo)), "indicadores"), (str((conf["confianca"] == "Alta").sum()), "com confiança alta"),
              (str(int(cont.get("automatizavel", 0))), "melhorias automatizáveis pelo painel"),
              (str(int(cont.get("com_acesso", 0))), "automatizáveis com acesso a dado"),
              (str(int(cont.get("setor", 0))), "dependem do setor")])

    doc.h1("Quadro geral")
    linhas = []
    for r in d.nucleo.itertuples():
        m = mel[mel["codigo"] == r.codigo]["tipo"].value_counts()
        c = conf.loc[r.codigo] if r.codigo in conf.index else None
        linhas.append([f"**{r.codigo}**", r.indicador, c.confianca if c is not None else "—", c.motivo if c is not None else "",
                       str(int(m.get("automatizavel", 0))), str(int(m.get("com_acesso", 0))), str(int(m.get("setor", 0)))])
    doc.tabela("Confiança no dado e melhorias por indicador",
               ["Código", "Indicador", "Confiança", "Por quê", "Automatizável", "Com acesso", "Setor"], linhas,
               num={4, 5, 6}, larg=[1.2, 4.2, 1.6, 10.5, 1.9, 1.8, 1.4])
    doc.nota("Confiança: Alta = dado completo de documento obrigatório e conferível; Média = dado completo com uma aproximação "
             "ou lacuna conhecida; Baixa = aproximação ou base pequena, o número orienta mas não comprova.")

    doc.h1("Achados desta verificação")
    doc.p("Pontos encontrados ao medir a captação dos dados, que pedem conferência ou correção:")
    doc.lista(achados(b))

    for r in d.nucleo.itertuples():
        doc.h1(f"{r.codigo} · {r.indicador}", id=r.codigo, quebra=True)
        c = conf.loc[r.codigo] if r.codigo in conf.index else None
        vals = d.valores.get(r.codigo, {})
        serie = "; ".join(f"{a}: {num(v, r.unidade)}{'' if comp else ' (parcial)'}" for a, (v, comp) in sorted(vals.items())
                          if v == v and a >= 2023)
        doc.ficha([("Fórmula", f"{r.formula} ({r.unidade})"), ("Valores", serie or "sem valor"),
                   ("Confiança no dado", f"{c.confianca}: {c.motivo}" if c is not None else "—"),
                   ("Responsável", r.responsavel)])
        txt, cab, lin, nota = captacao(b, r.codigo)
        doc.h2("1. O dado captado")
        doc.p(txt)
        if lin:
            doc.tabela(f"Captação do {r.codigo} por ano", cab, lin, num=set(range(1, len(cab))))
        if nota:
            doc.nota(nota)
        doc.h2("2. Como foi construído")
        doc.passos(CONSTRUCAO.get(r.codigo, []))
        doc.h2("3. O que validar")
        v = val[val["codigo"] == r.codigo]
        doc.tabela(f"Conferências do {r.codigo}", ["O que conferir", "Quem"], [[x.verificar, x.quem] for x in v.itertuples()],
                   larg=[18, 4])
        doc.h2("4. Melhorias")
        m = mel[mel["codigo"] == r.codigo].sort_values(["o", "tipo"])
        doc.tabela(f"Melhorias do {r.codigo}", ["Prioridade", "Tipo", "Melhoria", "Como fazer", "Quem"],
                   [[x.prioridade, TIPO[x.tipo], f"**{x.melhoria}**", x.como, x.quem] for x in m.itertuples()],
                   larg=[1.7, 3, 4, 11.5, 2.5])

    doc.h1("Plano de automação", quebra=True)
    doc.p("As melhorias de todos os indicadores reunidas pelo tipo, na ordem de prioridade. As automatizáveis pelo painel "
          "podem começar já; as que dependem de acesso viram pedidos formais a cada setor.")
    for tipo in ("automatizavel", "com_acesso", "setor"):
        m = mel[mel["tipo"] == tipo].sort_values(["o", "codigo"])
        doc.h2(f"{TIPO[tipo]} ({len(m)})")
        if tipo == "com_acesso":
            quem = m["quem"].str.split("/").explode().str.strip().value_counts()
            doc.p("Pedidos por setor: " + "; ".join(f"{k} ({v})" for k, v in quem.items()) + ".")
        doc.tabela(TIPO[tipo], ["Prioridade", "Indicador", "Melhoria", "Como fazer", "Quem"],
                   [[x.prioridade, f"**{x.codigo}**", x.melhoria, x.como, x.quem] for x in m.itertuples()],
                   larg=[1.7, 1.5, 4.5, 11.8, 2.5])

    hoje = date.today().strftime("%d/%m/%Y")
    meta = {"titulo": "Validação dos Indicadores do PLS", "eyebrow": "UFPB · Painel de Sustentabilidade · Núcleo do PLS",
            "h1": "Validação dos indicadores do núcleo do PLS UFPB",
            "subtitulo": "O dado captado, a construção, o que conferir e como melhorar",
            "lead": "Para cada um dos 15 indicadores: o que o painel realmente captou das fontes, como o valor foi "
                    "construído, as conferências pedidas à Comissão e aos setores e as melhorias, separadas pelo que pode "
                    "ser automatizado.",
            "selo": f"Versão de {hoje}",
            "nota_capa": f"Documento gerado pelo Painel de Sustentabilidade da UFPB em {hoje}. Os números de captação vêm "
                         "da última carga; as conferências e melhorias ficam em ref/validacao_nucleo.csv e "
                         "ref/validacao_melhorias.csv e podem ser ajustadas pela Comissão.",
            "rodape_doc": "PLS UFPB · Validação dos indicadores do núcleo", "rodape_html": "", "toc_niveis": 1,
            "paisagem": True}
    return doc, meta


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--saida", type=Path, default=Path(__file__).parent)
    a = ap.parse_args(argv)
    doc, meta = montar()
    a.saida.mkdir(parents=True, exist_ok=True)
    arq_html, arq_docx = a.saida / "validacao_indicadores_pls.html", a.saida / "validacao_indicadores_pls.docx"
    arq_html.write_text(html_doc(doc, meta), encoding="utf-8")
    docx_doc(doc, meta, arq_docx)
    print(f"{arq_html}\n{arq_docx}\n{doc.n_tab} tabelas")


if __name__ == "__main__":
    main()
