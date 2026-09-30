"""Fichas tecnicas dos 15 indicadores do nucleo do PLS UFPB.

    python relatorios/gerar_fichas_nucleo.py [--saida DIR]

Gera fichas_indicadores_pls.docx (Word) e fichas_indicadores_pls.html com, para
cada indicador: o que mede, formula, variaveis (campo e base de cada uma),
bases de dados, construcao passo a passo, regras e filtros, calculo ano a ano
(numerador, denominador, resultado), conferencias, limitacoes e como melhorar.

Textos de construcao: as familias de relatorios/gerar_construcao.py (as mesmas
da pagina de construcao dos indicadores). Textos proprios do nucleo, editaveis
pela Comissao em ref/: fichas_nucleo.csv (o que mede, polaridade,
periodicidade, responsavel), variaveis_nucleo.csv e melhorias_nucleo.csv.
"""

from __future__ import annotations

import argparse
import html
import re
import sys
from pathlib import Path

import pandas as pd

ETL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ETL))
from common import config  # noqa: E402
from common.storage import load_processed  # noqa: E402
from execucao.build_execucao import conjuntos, valores_nucleo  # noqa: E402
from metas import catalogo  # noqa: E402
from relatorios import gerar_construcao as gc  # noqa: E402
from relatorios.blocos import Doc, data_br, docx_doc, html_doc, num, vazio  # noqa: E402
from relatorios.exemplos_rastreados import rastrear  # noqa: E402

ANOS = [2023, 2024, 2025, 2026]
EXERCICIO = 2025  # ano dos exemplos rastreados (ultimo ano fechado)
ORDEM_PRIORIDADE = {"Alta": 0, "Média": 1, "Baixa": 2}
COLETA = {"automatizado": "Automatizada pelo painel", "informado": "Informada pelo setor responsável",
          "calcular": "Dado coletado, falta calcular", "fonte_nova": "Depende de fonte nova"}
DINHEIRO = {"pago", "pago_acao", "empenhado_itens", "empenhado_material_consumo", "pago_fornecedores",
            "contratacoes_pncp_valor"}
UNID_METRICA = {"consumo_kwh": "kWh", "consumo_m3": "m³", "consumo_litros": "L", "residuos_kg": "kg",
                "emissoes_kgco2e": "kg CO₂e", "co2e_kg": "kg CO₂e", "evg_pessoas_sust": "pessoas",
                "contratacoes_pncp": "contratações", "compras_compartilhadas": "compras"}


def limpar(txt: str) -> str:
    """HTML das familias de construcao -> marcacao dos blocos (**negrito**, `codigo`)"""
    s = re.sub(r"<code>(.*?)</code>", r"`\1`", str(txt))
    s = re.sub(r"</?(b|strong)>", "**", s)
    s = re.sub(r"<[^>]+>", "", s)
    return html.unescape(s)


# ------------------------------------------------------------------ familias sem regra `ind:`

FAMILIA_N08 = {
    "fontes": [("Monitoramento dos inversores das usinas fotovoltaicas (SINFRA)", None,
                "energia gerada por usina e por mês, no portal do fabricante dos inversores"),
               ("Faturas da Energisa nos processos de pagamento (SIPAC)", gc.SIPAC,
                "kWh consumido da rede, o mesmo do N01")],
    "passos": ["A SINFRA exporta a geração anual das usinas fotovoltaicas do monitoramento dos inversores.",
               "O valor é lançado no formulário de valores informados do painel, com a evidência (relatório do "
               "inversor), e entra em `data/metas/valores_informados.csv`.",
               "O painel soma a geração com o kWh consumido da rede no ano (faturas) e calcula a parcela renovável: "
               "geração ÷ (geração + consumo da rede) × 100."],
    "regras": ["Só geração própria (usinas nos campi). Energia comprada no mercado livre com certificado de origem "
               "não entra.", "Energia consumida da rede: mesma construção do N01."],
    "confere": ["O PLS registrou 3,69% em 2023 com os dados de monitoramento das usinas."],
    "limites": ["A geração consumida no próprio campus não passa pelo medidor da Energisa: as faturas não mostram a "
                "produção, e sem o lançamento da SINFRA o indicador fica vazio."],
}
FAMILIA_N15 = {
    "fontes": [("Plano de ações do PLS UFPB 2025–2029", None,
                "61 ações das Tabelas 16 a 24 e 9 rotinas de governança da seção 7, com responsável, início e fim "
                "(`ref/acoes_pls_ufpb.csv`)"),
               ("Formulário de acompanhamento do painel", None,
                "situação, percentual, evidência, justificativa, facilitadores, dificuldades e ajuste de cada ação, "
                "por ciclo semestral (`data/metas/acompanhamento_acoes.csv`)"),
               ("Dados do próprio painel", None,
                "verificação automática das ações contínuas de monitoramento (por exemplo, consumo de água medido "
                "todo mês)")],
    "passos": ["Carregar o plano de ações e o último registro de cada ação no formulário (`acoes/load_acoes.py`).",
               "Para ações com verificação pelo painel, conferir se a métrica ligada à ação tem dado nos últimos 6 "
               "meses.",
               "Classificar a situação de cada ação na data de referência (regras abaixo).",
               "Índice = ações concluídas, em dia ou em andamento (com evidência quando exigida) ÷ ações exigíveis "
               "× 100."],
    "regras": ["Início ainda não alcançado → “a iniciar” (não exigível). Suspensa ou cancelada → fora da conta.",
               "Ação contínua: realizada no ciclo ou verificada pelo painel → “em dia”; não realizada → “pendente”; "
               "sem registro → “sem informação”.",
               "Ação de entrega: concluída → “concluída”; prazo vencido com registro → “atrasada”; prazo vencido sem "
               "registro → “prazo vencido sem informação”; no prazo → situação informada ou “sem informação”.",
               "Concluída ou realizada sem evidência não conta como no prazo."],
    "confere": ["A situação de cada ação e a evidência verificada pelo painel ficam em `pls_acoes` para conferência."],
    "limites": ["Sem informação não quer dizer que a ação não foi feita: o índice depende do registro semestral "
                "dos setores.", "Todas as ações pesam igual, das rotinas às entregas estruturantes."],
}


# ------------------------------------------------------------------ dados

class Dados:
    def __init__(self):
        self.cat = catalogo.carregar()
        c = self.cat.set_index("id")
        self.metas = load_processed("pls_metas")
        self.acoes = load_processed("pls_acoes")
        nuc = conjuntos(self.cat)["nucleo"]
        self.valores = valores_nucleo(nuc, self.metas, self.acoes)
        ref = pd.read_csv(config.REF_DIR / "nucleo_pls.csv", sep=";", dtype=str, keep_default_na=False)
        fichas = pd.read_csv(config.REF_DIR / "fichas_nucleo.csv", sep=";", dtype=str, keep_default_na=False)
        # os textos da ficha (o que mede, polaridade por extenso, periodicidade, responsavel) vem de
        # fichas_nucleo.csv; o conjunto do nucleo ja traz versoes deles, que saem para nao duplicar
        repetidas = [c for c in fichas.columns if c != "codigo" and c in nuc.columns]
        self.nucleo = (nuc.drop(columns=["calculo", *repetidas]).merge(ref[["codigo", "observacao", "calculo", "indicador_catalogo"]],
                                                                        on="codigo").merge(fichas, on="codigo", how="left"))
        ids = self.nucleo["indicador_id"]
        self.nucleo["calculo_catalogo"] = ids.map(c["calculo"]).fillna("")
        self.nucleo["confirmar"] = ids.map(c["confirmar"]).fillna("")
        self.variaveis = pd.read_csv(config.REF_DIR / "variaveis_nucleo.csv", sep=";", dtype=str, keep_default_na=False)
        self.melhorias = pd.read_csv(config.REF_DIR / "melhorias_nucleo.csv", sep=";", dtype=str, keep_default_na=False)
        self.decisoes = pd.read_csv(config.REF_DIR / "decisoes_comissao.csv", sep=";", dtype=str, keep_default_na=False)
        self.fontes = pd.read_csv(config.REF_DIR / "fontes_extracao.csv", sep=";", dtype=str,
                                  keep_default_na=False).set_index("fonte")
        self.eixos = pd.read_csv(config.REF_DIR / "eixos_pls.csv", sep=";", dtype=str).set_index("eixo_pls")["eixo"]
        self.data_ref = str(self.acoes["data_referencia"].iloc[0]) if not self.acoes.empty else ""

    def calc(self, r) -> dict | None:
        regra = r.calculo_catalogo or r.calculo
        return catalogo.parse_calculo(regra) if regra else None

    def familia(self, r) -> dict:
        if r.codigo == "N08":
            return FAMILIA_N08
        if r.codigo == "N15":
            return FAMILIA_N15
        calc = self.calc(r)
        fam = gc.FAMILIAS[calc["metrica"]] if calc["metrica"] in gc.FAMILIAS else gc.FAMILIA_EVG
        return fam

    def situacao(self, r, ano: int) -> str:
        if not r.indicador_id or self.metas.empty:
            return ""
        m = self.metas[(self.metas["indicador_id"] == r.indicador_id) & (self.metas["ano"] == ano)]
        if m.empty:
            return ""
        sit = str(m["situacao"].iloc[0])
        return {"acompanhamento": "", "historico": "histórico", "linha_de_base": "linha de base",
                "atingida": "meta atingida", "nao_atingida": "meta não atingida",
                "em_andamento": "em andamento"}.get(sit, sit.replace("_", " "))


# ------------------------------------------------------------------ calculo ano a ano

def tabela_calculo(d: Dados, r) -> tuple[list[str], list[list], str]:
    """cabecalho, linhas e nota da tabela numerador/denominador/resultado"""
    cab = ["Ano", "Meses com dado", "Numerador", "Denominador", "Resultado", "Situação"]
    unidade = r.unidade
    if r.codigo == "N15":
        a = d.acoes
        if a.empty:
            return cab, [], ""
        exig = a[a["exigivel"]]
        no_prazo = exig["situacao"].isin(["concluida", "em_dia", "em_andamento"]) & ~exig["sem_evidencia"]
        linha = [f"Posição em {data_br(d.data_ref)}", "—", f"{int(no_prazo.sum())} ações no prazo",
                 f"{len(exig)} ações exigíveis", f"{num(a['indice_cumprimento'].iloc[0])}%", "fotografia do ciclo"]
        return cab, [linha], "O índice é uma fotografia na data de referência, não uma soma anual."
    calc = d.calc(r)
    if calc is None:
        return cab, [], "Sem valor no painel: o dado ainda depende do lançamento do setor."
    sel = gc._selecao(calc)
    meses = gc._meses_carregados(calc["metrica"])
    dinheiro = calc["metrica"] in DINHEIRO
    unid_num = "R$" if dinheiro else UNID_METRICA.get(calc["metrica"], "")
    linhas = []
    for ano in ANOS:
        s = sel[sel["ano"] == ano]
        if s.empty and not d.valores.get(r.codigo, {}).get(ano):
            continue
        numer = s["valor_real" if dinheiro else "valor_nominal"].sum()
        if calc["campo"] == "valor_real_per_capita":
            den = f"{num(s['comunidade'].max())} pessoas (comunidade de {int(s['ano_comunidade'].max())})" if len(s) else "—"
        elif calc["campo"] == "pct_servidores":
            den = f"{num(s['servidores'].max())} servidores" if len(s) else "—"
        elif calc["campo"] == "valor_por_m2":
            den = f"{num(s.drop_duplicates('area_m2')['area_m2'].sum())} m²"
        elif calc.get("razao_subtemas"):
            base = gc.ind[(gc.ind["metrica"] == calc["metrica"]) & gc.ind["subtema"].isin(calc["razao_subtemas"])
                          & (gc.ind["ano"] == ano)]
            if calc["tema"]:
                base = base[base["tema_codigo"] == calc["tema"]]
            den = f"{num(base['valor_real' if dinheiro else 'valor_nominal'].sum(), unid_num)} {'' if dinheiro else unid_num}"
        else:
            den = "—"
        v, completo = d.valores.get(r.codigo, {}).get(ano, (None, None))
        res = "—" if vazio(v) else f"{num(v, unidade)} {'' if unidade == 'R$' else unidade}".strip()
        n_txt = f"{num(numer, unid_num)} {'' if dinheiro else unid_num}".strip()
        if r.codigo == "N03":
            n_txt += f" (= {num(numer / 1000)} t)"
        sit = d.situacao(r, ano)
        if completo is False:
            sit = ", ".join(x for x in ("ano parcial", sit) if x)
        linhas.append([str(ano), str(meses.get(ano, 0)), n_txt, den.strip(), res, sit or "—"])
    nota = (f"Valores em R$ corrigidos pelo IPCA para {gc.REF_IPCA_TXT}. " if dinheiro else "")
    nota += "Ano com menos de 12 meses de dado carregado fica marcado como parcial e não é usado para avaliar meta."
    return cab, linhas, nota


# ------------------------------------------------------------------ conteudo

def ficha(doc: Doc, d: Dados, r):
    doc.h1(f"{r.codigo} · {r.indicador}", anexo=True, id=r.codigo, quebra=True)
    eixo = f"Eixo {r.eixo_pls} · {d.eixos[r.eixo_pls]}" if r.eixo_pls in d.eixos.index else "Transversal · Gestão do PLS"
    cat_ids = r.indicador_catalogo.replace("|", ", ") if r.indicador_catalogo else "—"
    doc.nota(f"{eixo} · indicador do catálogo do painel: {cat_ids}")
    meta = r.meta or (f"Sem meta fixada. Sugestão: {r.meta_sugerida}" if r.meta_sugerida else "Sem meta fixada")
    doc.ficha([("O que mede", r.o_que_mede), ("Fórmula", r.formula), ("Unidade", r.unidade),
               ("Leitura", r.polaridade), ("Periodicidade", r.periodicidade), ("Meta", meta),
               ("Responsável", r.responsavel), ("Coleta", COLETA.get(r.automacao, r.automacao)),
               ("Fonte", r.fonte),
               ("Regra no painel", f"`{r.calculo_catalogo or r.calculo}`" if (r.calculo_catalogo or r.calculo) else "")])
    fam = d.familia(r)

    doc.h2("1. Como é medido")
    doc.p(f"**Fórmula:** {r.formula} ({r.unidade}).")
    if r.observacao:
        doc.p(r.observacao.rstrip(".") + ".")
    if r.codigo == "N03":
        doc.p("O painel calcula as emissões em kg CO₂e por mês e as apresenta em toneladas (÷ 1.000).")

    doc.h2("2. Variáveis")
    v = d.variaveis[d.variaveis["codigo"] == r.codigo]
    doc.tabela(f"Variáveis do {r.codigo}", ["Papel", "Variável", "Descrição", "Base de dados", "Campos"],
               [[x.papel, f"**{x.variavel}**", x.descricao, x.base,
                 ", ".join(f"`{c.strip()}`" for c in x.campos.split(","))] for x in v.itertuples()],
               larg=[0.9, 1.4, 2.8, 2.2, 1.9])

    doc.h2("3. Como os dados são retirados")
    doc.p("Cada fonte abaixo com o endereço exato, o formato, como o painel obtém o dado, os filtros aplicados na "
          "retirada, os campos usados, onde fica a cópia e como conferir à mão.")
    if r.codigo == "N08":
        doc.p("**Monitoramento dos inversores das usinas fotovoltaicas (SINFRA):** portal do fabricante dos "
              "inversores, ainda sem integração. A geração anual é lançada pela SINFRA no formulário de valores "
              "informados do painel, com o relatório do inversor como evidência.")
    for f in r.fontes.split("|"):
        x = d.fontes.loc[f]
        doc.h3(x.nome)
        doc.ficha([("Endereço", x.endereco), ("Formato", x.formato), ("Como o painel obtém", x.como_obtem),
                   ("Atualização", x.periodicidade), ("Filtros na retirada", "" if x.filtros == "—" else x.filtros),
                   ("Campos usados", x.campos), ("Cópia guardada", f"`{x.copia_local}`"),
                   ("Como conferir à mão", x.conferir_a_mao)])

    doc.h2("4. Construção passo a passo")
    doc.passos([limpar(p) for p in fam["passos"]])

    doc.h2("5. Regras e filtros")
    regras = list(fam["regras"])
    calc = d.calc(r) if r.codigo not in ("N08", "N15") else None
    if calc:
        regras += gc._regras_especificas(r, calc)
    doc.lista([limpar(x) for x in regras] or ["Sem filtro além dos descritos na construção."])

    doc.h2("6. Cálculo ano a ano")
    cab, linhas, nota = tabela_calculo(d, r)
    if linhas:
        doc.tabela(f"Cálculo do {r.codigo} por ano", cab, linhas, num={1, 2, 3, 4}, larg=[1.3, 0.9, 1.9, 1.9, 1.5, 1.5])
    if nota:
        doc.nota(nota)

    doc.h2("7. Exemplo rastreado: da fonte ao indicador")
    doc.p("Um registro real seguido desde a fonte até o valor do indicador, para refazer a conta à mão.")
    rastrear(doc, r.codigo, EXERCICIO)

    doc.h2("8. Conferências realizadas")
    doc.lista([limpar(x) for x in fam["confere"]] or ["Ainda sem conferência com fonte independente."])

    doc.h2("9. Limitações conhecidas")
    limites = [limpar(x) for x in fam["limites"]]
    if r.confirmar and not any(r.confirmar in x for x in limites):
        limites.append(f"**A confirmar pela Comissão:** {r.confirmar}")
    doc.lista(limites)

    dec = d.decisoes[d.decisoes["indicadores"].str.split("|").map(lambda c: r.codigo in c or r.indicador_id in c)]
    if not dec.empty:
        doc.h3("Decisões pendentes da Comissão do PLS")
        doc.tabela(f"Decisões sobre o {r.codigo}", ["", "Questão", "Contexto", "Opções", "Efeito no indicador"],
                   [[x.id, f"**{x.questao}**", x.contexto, x.opcoes, x.efeito]
                    for x in dec.itertuples() if x.situacao == "pendente"],
                   larg=[0.5, 1.6, 2.6, 2.2, 1.9])

    doc.h2("10. Como melhorar o indicador")
    m = d.melhorias[d.melhorias["codigo"] == r.codigo].copy()
    m["o"] = m["prioridade"].map(ORDEM_PRIORIDADE)
    doc.tabela(f"Melhorias propostas para o {r.codigo}", ["Prioridade", "Frente", "Melhoria", "Quem"],
               [[x.prioridade, x.frente, x.melhoria, x.responsavel] for x in m.sort_values(["o", "frente"]).itertuples()],
               larg=[0.9, 1, 4.6, 1.5])


def introducao(doc: Doc, d: Dados):
    doc.h1("Como ler as fichas", anexo=True)
    auto = int((d.nucleo["automacao"] == "automatizado").sum())
    doc.p(f"Este documento descreve a construção dos {len(d.nucleo)} indicadores do núcleo do Plano de Logística "
          f"Sustentável da UFPB, o conjunto usado no painel geral e no índice sintético de execução. Hoje {auto} são "
          f"calculados automaticamente pelo painel a partir de dados abertos e documentos públicos; os demais dependem "
          f"de informação dos setores.")
    doc.p("Cada ficha traz um quadro-resumo e dez partes, sempre na mesma ordem:")
    doc.passos(["**Como é medido:** a fórmula e o que ela deixa de fora.",
                "**Variáveis:** cada termo da fórmula, com a base e os campos de onde sai.",
                "**Como os dados são retirados:** para cada fonte, o endereço exato, o formato, como o painel "
                "obtém o dado, os filtros, os campos usados, onde fica a cópia e como conferir à mão.",
                "**Construção passo a passo:** o caminho do dado bruto até o valor do ano.",
                "**Regras e filtros:** naturezas de despesa, expressões de texto, fatores e critérios aplicados.",
                "**Cálculo ano a ano:** numerador, denominador e resultado de 2023 a 2026.",
                "**Exemplo rastreado:** um registro real (processo, pagamento, empenho, contratação) seguido da fonte "
                "até o valor do indicador.",
                "**Conferências realizadas:** comparações com fontes independentes.",
                "**Limitações conhecidas:** o que o número ainda não mede bem.",
                "**Como melhorar o indicador:** propostas por frente (dado, método, meta, automação, gestão), com "
                "responsável e prioridade."])
    doc.h2("Caminho do dado no painel")
    doc.passos(["**Coleta:** o painel baixa os arquivos das fontes (Portal da Transparência, SIPAC, PNCP, INEP, "
                "ENAP, Receita Federal, IBGE) e guarda uma cópia em `data/raw`, para não baixar de novo.",
                "**Tratamento:** cada módulo limpa e padroniza os dados em tabelas `pls_*` em `data/processed` "
                "(despesas, faturas, compras, cursos, fornecedores), sem nomes nem CPF (LGPD).",
                "**Métricas mensais:** `pls_indicadores` soma cada métrica por mês, tema e subtema, com o valor "
                "nominal, o corrigido pelo IPCA, por pessoa, por m² e em % dos servidores.",
                "**Valor anual:** `pls_metas` soma os meses do ano, marca o ano completo (12 meses com dado), compara "
                "com a meta e calcula o alcance; `pls_execucao` leva o valor ao núcleo.",
                "**Atualização:** a carga completa roda todo mês e os formulários dos setores entram todo dia."])
    doc.p(f"Valores em reais são corrigidos pelo IPCA para {gc.REF_IPCA_TXT}. Quando um mês não tem dado carregado, "
          f"o ano fica marcado como parcial e não é usado para avaliar meta. Nas métricas de contratação, mês sem "
          f"contratação publicada não é mês sem dado.")
    linhas = []
    for r in d.nucleo.itertuples():
        anos = [a for a in d.valores.get(r.codigo, {}) if d.valores[r.codigo][a][1]]
        ult = max(anos) if anos else None
        v = d.valores[r.codigo][ult][0] if ult else None
        linhas.append([f"**{r.codigo}**", r.indicador, r.unidade, COLETA.get(r.automacao, r.automacao).split(" ")[0],
                       f"{num(v, r.unidade)} ({ult})" if ult else "—"])
    doc.tabela("Indicadores do núcleo", ["Código", "Indicador", "Unidade", "Coleta", "Último ano completo"], linhas,
               num={4}, larg=[0.7, 3.2, 1.2, 1.3, 1.6])


def sintese(doc: Doc, d: Dados):
    doc.h1("Síntese das melhorias", anexo=True, quebra=True)
    m = d.melhorias
    doc.p(f"As fichas trazem {len(m)} propostas de melhoria. A tabela abaixo conta as propostas por frente e prioridade; "
          f"a seguinte lista as de prioridade alta, que são as que mais mudam a confiança nos números.")
    tab = m.groupby(["frente", "prioridade"]).size().unstack(fill_value=0)
    cols = [c for c in ORDEM_PRIORIDADE if c in tab.columns]
    doc.tabela("Propostas por frente e prioridade", ["Frente", *cols, "Total"],
               [[f, *[int(tab.loc[f, c]) for c in cols], int(tab.loc[f].sum())] for f in tab.index],
               num=set(range(1, len(cols) + 2)), larg=[2, 1, 1, 1, 1])
    alta = m[m["prioridade"] == "Alta"]
    doc.tabela("Melhorias de prioridade alta", ["Indicador", "Frente", "Melhoria", "Quem"],
               [[f"**{x.codigo}**", x.frente, x.melhoria, x.responsavel] for x in alta.itertuples()],
               larg=[0.8, 1, 4.7, 1.5])
    quem = alta["responsavel"].str.split("/").explode().str.strip().value_counts()
    doc.p("Quem concentra as melhorias de prioridade alta: " + "; ".join(f"{k} ({v})" for k, v in quem.items()) + ".")


def retirada(doc: Doc, d: Dados):
    """Visao geral da retirada dos dados: todas as fontes, controles automaticos e como reproduzir."""
    doc.h1("Como os dados são retirados", anexo=True, quebra=True)
    doc.p("O painel usa fontes públicas, informações registradas pelos setores com evidência e uma única planilha "
          "institucional: a contagem anual da comunidade acadêmica da UFPB (discentes, docentes, técnicos e "
          "terceirizados), usada como denominador por pessoa e de servidores. Ela é importada sem digitação, com "
          "conferência da soma, e fica versionada em `ref/comunidade_ufpb.csv`. Os demais números podem ser refeitos "
          "a partir do endereço da fonte, e a cópia exata do que foi lido fica guardada no servidor do painel.")
    usos: dict[str, list[str]] = {}
    for r in d.nucleo.itertuples():
        for f in r.fontes.split("|"):
            usos.setdefault(f, []).append(r.codigo)
    linhas = [[f"**{x.nome}**", x.endereco, x.periodicidade, ", ".join(usos.get(f, []))]
              for f, x in d.fontes.iterrows() if f in usos]
    doc.tabela("Fontes de dados do núcleo", ["Fonte", "Endereço", "Atualização", "Indicadores"],
               linhas, larg=[2.3, 3.2, 1.5, 1.1])
    doc.nota("Como o painel obtém cada fonte, os filtros, os campos e como conferir à mão estão na parte 3 de cada ficha.")
    doc.h2("Princípios da retirada")
    doc.lista([
        "**Dado de processo obrigatório:** pagamento no Portal da Transparência, fatura anexada ao processo de "
        "pagamento no SIPAC, edital no PNCP. O dado existe porque a despesa ou a compra aconteceu, "
        "não porque alguém preencheu uma planilha para o PLS.",
        "**Cópia do que foi lido:** cada arquivo ou documento lido fica registrado em `data/raw` (linhas da UFPB, "
        "resultado da leitura de cada processo, texto dos editais). Uma nova carga não baixa de novo o que já foi lido, "
        "e uma auditoria compara o painel com a cópia.",
        "**Regras em tabelas, não no código:** classificação de naturezas de despesa, regras de texto, critérios dos "
        "editais, fatores de emissão, correções de número de processo e área construída ficam em arquivos `ref/*.csv` "
        "que a Comissão pode ler e pedir para alterar.",
        "**LGPD:** nome, CPF, matrícula e dados de condutores e servidores são descartados na leitura. Pessoas só "
        "aparecem em contagens.",
        "**Ano completo:** um ano só é comparado com a meta quando todos os meses da fonte foram carregados. Nas "
        "contratações, mês sem compra publicada não é mês faltando.",
    ])
    doc.h2("Controles automáticos a cada carga")
    doc.p("Depois de cada carga mensal o painel roda uma verificação e avisa por e-mail o que ficou pendente:")
    doc.lista([
        "Despesas: último mês carregado e dias sem arquivo publicado pela CGU.",
        "Faturas: processos de pagamento sem fatura legível ou não achados no SIPAC, meses sem consumo lido e "
        "unidades consumidoras com variação anual acima de 50%.",
        "Contratações: editais sem documento legível.",
        "Escola Virtual de Governo: bimestres sem arquivo publicado.",
        "Comunidade acadêmica da UFPB: planilha sem o ano anterior. INEP e IPCA: último ano ou mês disponível.",
        "Fator de emissão do SIN: meses ainda não publicados pelo MCTI.",
        "Cadastro de fornecedores: pagamentos a CNPJ sem porte ou UF.",
        "Plano de ações e metas: ações vencidas sem registro e indicadores informados sem valor.",
    ])
    doc.h2("Como reproduzir")
    doc.passos([
        "O código do painel (`pls_ufpb-etl`) roda com Python e só usa bibliotecas abertas.",
        "`python run.py mensal` baixa e processa todas as fontes; `python run.py <modulo>` processa uma fonte só "
        "(ex.: `faturas`, `compras`, `fator_sin`).",
        "As tabelas intermediárias ficam em `data/processed/*.parquet` (uma por módulo) e podem ser abertas em "
        "qualquer ferramenta de análise de dados para conferência.",
        "Cada ficha abaixo traz um exemplo rastreado com os números de processo, pagamento, empenho ou contratação "
        "para refazer a conta na fonte original.",
    ])


def montar() -> tuple[Doc, dict]:
    d = Dados()
    doc = Doc()
    introducao(doc, d)
    retirada(doc, d)
    for r in d.nucleo.itertuples():
        ficha(doc, d, r)
    sintese(doc, d)
    gerado = data_br(d.data_ref) if d.data_ref else ""
    meta = {"titulo": "Fichas dos Indicadores do PLS",
            "eyebrow": "UFPB · Painel de Sustentabilidade · Núcleo do PLS",
            "h1": "Fichas técnicas dos indicadores do núcleo do PLS UFPB",
            "subtitulo": "Como cada indicador é medido e como melhorá-lo",
            "lead": "Para cada um dos 15 indicadores: o que mede, variáveis, bases de dados, construção passo a passo, "
                    "cálculo ano a ano, conferências, limitações e propostas de melhoria.",
            "selo": f"Gerado a partir dos dados do painel em {gerado}",
            "nota_capa": f"Documento gerado pelo Painel de Sustentabilidade da UFPB em {gerado}. As propostas de "
                         f"melhoria e as descrições ficam em ref/melhorias_nucleo.csv, ref/variaveis_nucleo.csv e "
                         f"ref/fichas_nucleo.csv, e podem ser ajustadas pela Comissão.",
            "rodape_doc": "PLS UFPB · Fichas técnicas dos indicadores do núcleo", "toc_niveis": 1,
            "rodape_html": "Painel de Sustentabilidade da UFPB. A versão em Word destas fichas é gerada junto com "
                           "esta página."}
    return doc, meta


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--saida", type=Path, default=Path(__file__).parent)
    a = ap.parse_args(argv)
    doc, meta = montar()
    a.saida.mkdir(parents=True, exist_ok=True)
    arq_html, arq_docx = a.saida / "fichas_indicadores_pls.html", a.saida / "fichas_indicadores_pls.docx"
    arq_html.write_text(html_doc(doc, meta), encoding="utf-8")
    docx_doc(doc, meta, arq_docx)
    print(f"{arq_html}\n{arq_docx}\n{sum(b['t'] == 'h1' for b in doc.blocos)} seções, {doc.n_tab} tabelas")


if __name__ == "__main__":
    main()
