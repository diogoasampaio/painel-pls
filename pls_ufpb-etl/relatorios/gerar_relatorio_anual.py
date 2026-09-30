"""Relatorio Anual de Avaliacao de Desempenho do PLS UFPB (minuta gerada pelo painel).

    python relatorios/gerar_relatorio_anual.py [--ano 2025] [--saida DIR]

Gera, para o exercicio (padrao: ultimo ano fechado), a mesma minuta em dois
formatos: relatorio_pls_<ano>.docx (editavel, para a Comissao completar e
juntar ao processo no SEI) e relatorio_pls_<ano>.html (versao web).

O conteudo e montado uma vez como lista de blocos (titulo, paragrafo, tabela,
pendencia...) e cada formato so desenha os blocos. Os numeros vem das bases
do ETL (pls_execucao, pls_metas, pls_acoes, pls_compras, pls_pagamentos_pj,
pls_saude_carga); o texto de analise sai esbocado a partir deles. O que
depende da Comissao (composicao, reunioes, analise qualitativa, metas ainda
nao fixadas) sai como bloco "A preencher", destacado nos dois formatos.
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import date
from pathlib import Path

import pandas as pd

ETL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ETL))
from common import config  # noqa: E402
from common.storage import load_processed  # noqa: E402
from execucao.build_execucao import conjuntos, valores_nucleo  # noqa: E402
from metas import catalogo  # noqa: E402
from relatorios.blocos import (FAIXA_ROT, Doc, data_br, docx_doc, fx, html_doc, mi, num, pct,  # noqa: E402
                               vazio)

PAINEL = "https://claude.ai/artifact/SRZrgVdM3XnRT9QTfP6qk5"
FICHAS = "https://claude.ai/artifact/WzARzGDgoTKjA8GNNhCbu7"
LIMITE_VARIACAO = 30  # % de variacao anual que pede conferencia da serie antes de publicar
ORDEM_EIXOS = ["1", "2", "3", "4", "5", "6", "transversal"]

ACAO_ROT = {"concluida": "Concluída", "em_dia": "Em dia (ação contínua)", "em_andamento": "Em andamento",
            "nao_iniciada": "Não iniciada", "a_iniciar": "A iniciar (prazo futuro)", "pendente": "Pendente no ciclo",
            "atrasada": "Atrasada", "vencida_sem_informacao": "Prazo vencido sem informação",
            "sem_informacao": "Sem informação", "suspensa": "Suspensa", "cancelada": "Cancelada"}
AUTOMACAO_ROT = {"automatizado": "Automatizado", "calcular": "Falta calcular", "fonte_nova": "Fonte nova",
                 "informado": "Informado pelo setor"}
NIVEL_ROT = {"especifico": "Critério específico obrigatório", "preferencial": "Só cláusula de preferência",
             "generico": "Menção genérica", "nenhum": "Nenhuma menção", "sem_texto": "Documento sem texto (escaneado)",
             "sem_documento": "Sem documento publicado", "nao_lido": "Não lido (inexigibilidade)", "erro": "Erro de leitura"}


# ------------------------------------------------------------------ dados

class Dados:
    def __init__(self, ano: int):
        self.ano = ano
        cat = catalogo.carregar()
        self.metas = load_processed("pls_metas")
        self.acoes = load_processed("pls_acoes")
        self.nucleo = conjuntos(cat)["nucleo"]
        ref = pd.read_csv(config.REF_DIR / "nucleo_pls.csv", sep=";", dtype=str, keep_default_na=False)
        self.nucleo = self.nucleo.merge(ref[["codigo", "observacao", "hoje"]], on="codigo", how="left")
        self.valores = valores_nucleo(self.nucleo, self.metas, self.acoes)
        self.eixos = pd.read_csv(config.REF_DIR / "eixos_pls.csv", sep=";", dtype=str).set_index("eixo_pls")
        self.faixas = pd.read_csv(config.REF_DIR / "faixas_execucao.csv", sep=";", dtype=str, keep_default_na=False)
        self.param = pd.read_csv(config.REF_DIR / "indice_execucao.csv", sep=";", dtype=str).set_index("parametro")
        ex = load_processed("pls_execucao")
        self.execucao = ex[ex["conjunto"] == "nucleo"] if not ex.empty else ex
        self.compras = load_processed("pls_compras")
        self.compartilhadas = load_processed("pls_compras_compartilhadas")
        self.pagamentos = load_processed("pls_pagamentos_pj")
        self.saude = load_processed("pls_saude_carga")
        if not self.saude.empty:  # so a ultima verificacao
            self.saude = self.saude[self.saude["execucao"] == self.saude["execucao"].max()]
        arq = config.DATA_DIR / "metas" / "acompanhamento_acoes.csv"
        self.acomp = (pd.read_csv(arq, sep=";", dtype=str, keep_default_na=False) if arq.exists() else pd.DataFrame())
        self.data_ref = str(self.acoes["data_referencia"].iloc[0]) if not self.acoes.empty else date.today().isoformat()

    def geral(self, ano: int) -> pd.Series | None:
        g = self.execucao[(self.execucao["nivel"] == "geral") & (self.execucao["ano"] == ano)]
        return g.iloc[0] if not g.empty else None

    def ind_ano(self, ano: int) -> pd.DataFrame:
        e = self.execucao
        return e[(e["nivel"] == "indicador") & (e["ano"] == ano)].set_index("codigo")

    def eixo_ano(self, ano: int) -> pd.DataFrame:
        e = self.execucao
        return e[(e["nivel"] == "eixo") & (e["ano"] == ano)].set_index("eixo_pls")

    def valor(self, codigo: str, ano: int) -> tuple[float | None, bool | None]:
        return self.valores.get(codigo, {}).get(ano, (None, None))

    def nome_eixo(self, eixo: str) -> str:
        return self.eixos["eixo"].get(eixo, "Gestão do PLS (transversal)")


def comentario(d: Dados, r, ano: int, info) -> str:
    """Leitura automatica de um indicador no exercicio."""
    v, completo = d.valor(r.codigo, ano)
    va, completo_a = d.valor(r.codigo, ano - 1)
    un = r.unidade
    if vazio(v):
        motivo = r.hoje or r.observacao or "a fonte ainda não está integrada ao painel"
        return f"**{r.codigo} {r.indicador}:** sem valor em {ano}. {motivo.rstrip('.')}."
    frase = f"**{r.codigo} {r.indicador}:** {num(v, un)} {'' if un == 'R$' else un} em {ano}".replace("  ", " ")
    if not completo:
        frase += " (ano ainda sem os 12 meses)"
    if not vazio(va) and va:
        var = 100 * (v - va) / abs(va)
        sentido = "aumento" if var > 0 else "redução"
        frase += f", {sentido} de {pct(abs(var))} em relação a {ano - 1} ({num(va, un)})"
        if completo and completo_a and abs(var) > LIMITE_VARIACAO:
            frase += (f". Variação acima de {LIMITE_VARIACAO}%: conferir a série com o setor responsável antes de "
                      "publicar")
    frase += ". "
    faixa = info.get("faixa") if info is not None else None
    alc = info.get("alcance_pct") if info is not None else None
    if faixa == "atingida":
        frase += f"Meta ({r.meta}) atingida."
    elif faixa in ("proxima", "progresso", "distante"):
        frase += f"Meta: {r.meta}. Alcance de {pct(alc, 0)} da meta ({FAIXA_ROT[faixa].lower()})."
    elif faixa == "nao_avaliavel":
        frase += f"Meta: {r.meta}. O ano ainda não permite avaliar a meta (linha de base ou ano parcial)."
    else:
        frase += "Indicador de acompanhamento, ainda sem meta fixada pela Comissão"
        frase += f" (sugestão: {r.meta_sugerida.rstrip('.')})." if r.meta_sugerida else "."
    return frase


def secao_apresentacao(doc: Doc, d: Dados):
    ano = d.ano
    doc.h1("Apresentação")
    doc.p(f"Este relatório apresenta a avaliação de desempenho do Plano de Logística Sustentável da Universidade "
          f"Federal da Paraíba (PLS UFPB 2025–2029) no exercício de {ano}, em atendimento ao Decreto nº 7.746/2012 "
          f"e à Portaria SEGES/MGI nº 5.376/2023, que pedem o acompanhamento anual dos resultados do plano e a "
          f"sua publicação.")
    doc.p("Os números vêm do Painel de Sustentabilidade da UFPB, que reúne automaticamente dados abertos do "
          "Portal da Transparência, das faturas de água e energia anexadas aos processos de pagamento, do Censo da "
          "Educação Superior (INEP), do Compras.gov.br e do PNCP, do cadastro de CNPJ da Receita Federal e da "
          "Escola Virtual de Governo. Os setores responsáveis registram o andamento das ações e os indicadores "
          "que não têm fonte pública em formulários próprios do painel.")
    doc.p(f"O relatório é uma minuta gerada pelo painel em {data_br(d.data_ref)}. A Comissão Gestora do PLS "
          f"completa as partes marcadas como “A preencher”, valida os números e aprova a versão final.")
    doc.pendente("Composição da Comissão Gestora do PLS (portaria de designação), reuniões realizadas no exercício "
                 "e principais deliberações.")


def secao_metodologia(doc: Doc, d: Dados):
    doc.h1("Como o desempenho é medido")
    n = len(d.nucleo)
    auto = int((d.nucleo["automacao"] == "automatizado").sum())
    doc.p(f"A avaliação usa o núcleo do PLS: {n} indicadores escolhidos entre os do plano e os do Caderno de "
          f"Logística Sustentável, cobrindo os seis eixos e a gestão do próprio plano. Hoje {auto} deles são "
          f"calculados automaticamente pelo painel; os demais dependem de informação dos setores. A ficha de cada "
          f"indicador (fórmula, fonte e limitações) está no Anexo A.")
    doc.h2("Alcance e faixas de execução")
    doc.p("Para cada indicador com meta, o painel calcula o alcance no ano, de 0 a 100%: quanto da meta foi "
          "cumprido. Em metas de redução ou aumento em relação a um ano-base, o alcance é a variação obtida sobre "
          "a variação pedida; piora em relação ao ano-base vale 0 e meta superada vale 100. O alcance coloca o "
          "indicador em uma faixa:")
    doc.tabela("Faixas de execução dos indicadores", ["Faixa", "Critério"],
               [[fx(r.codigo), r.descricao] for r in d.faixas.itertuples()], larg=[1, 3],
               fonte="parâmetros do painel, a validar pela Comissão")
    doc.h2("Índice sintético de execução")
    pm, pa = float(d.param.loc["peso_metas", "valor"]), float(d.param.loc["peso_acoes", "valor"])
    doc.p(f"O índice sintético resume a execução do plano em um número de 0 a 100. Ele combina o alcance médio das "
          f"metas dos indicadores (peso {pct(100 * pm / (pm + pa), 0)}) com o cumprimento do plano de ações, o "
          f"indicador N15 (peso {pct(100 * pa / (pm + pa), 0)}). O alcance das metas é a média de cada eixo e depois "
          f"a média dos eixos, para que um eixo com muitos indicadores não pese mais que os outros. Quando falta "
          f"um dos componentes, o outro vale sozinho.")
    doc.p("O índice vem sempre acompanhado da cobertura: a parte dos indicadores com meta que puderam ser "
          "avaliados no ano. Índice alto com cobertura baixa diz pouco sobre o plano como um todo.")


def secao_visao_geral(doc: Doc, d: Dados):
    ano = d.ano
    doc.h1(f"Visão geral da execução em {ano}")
    g = d.geral(ano)
    ind = d.ind_ano(ano)
    if g is None:
        doc.pendente(f"O painel ainda não calculou a execução de {ano}. Rodar o módulo execucao do ETL.")
        return
    doc.kpis([(pct(g["indice_sintetico"]), "índice sintético de execução"),
              (f"{int(g['n_avaliados'])} de {int(g['n_indicadores'])}", "indicadores com meta avaliada"),
              (f"{int(g['n_indicadores'] - g['n_com_meta'])}", "indicadores ainda sem meta"),
              (pct(g["indice_acoes"]) if not vazio(g["indice_acoes"]) else "—", "cumprimento das ações (N15)")])
    comp = "só o alcance das metas" if g["componentes"] == "metas" else "alcance das metas e cumprimento das ações"
    doc.p(f"Em {ano}, o índice sintético do núcleo foi de **{pct(g['indice_sintetico'])}**, calculado com {comp}. "
          f"Só {int(g['n_avaliados'])} dos {int(g['n_indicadores'])} indicadores tinham meta avaliável no ano, "
          f"porque a Comissão ainda não fixou meta para os demais. O número, portanto, mostra o desempenho desses "
          f"{int(g['n_avaliados'])} indicadores, e não do plano inteiro.")
    if vazio(g["indice_acoes"]):
        doc.p(f"O componente de ações não entra em {ano}: o acompanhamento semestral das ações começou a ser "
              f"registrado no painel depois do exercício (ver seção 5).")
    doc.faixas([(c, int(g[f"faixa_{c}"])) for c in FAIXA_ROT])
    avaliados = ind[ind["alcance_pct"].notna()]
    if not avaliados.empty:
        doc.tabela(f"Indicadores com meta avaliada em {ano}", ["Indicador", "Meta", "Valor", "Alcance", "Faixa"],
                   [[f"{c} {r['indicador']}", r["meta"], f"{num(r['valor'])} {r['unidade']}", pct(r["alcance_pct"], 0),
                     fx(r["faixa"])] for c, r in avaliados.iterrows()], num={2, 3}, larg=[3, 1.6, 1.4, 0.9, 1.3])
    ex = d.eixo_ano(ano)
    linhas = []
    for e in ORDEM_EIXOS:
        if e not in ex.index:
            continue
        r = ex.loc[e]
        linhas.append([f"{'Eixo ' + e if e != 'transversal' else 'Transversal'} · {d.nome_eixo(e)}",
                       int(r["n_indicadores"]), int(r["n_avaliados"]), pct(r["indice_metas"])])
    doc.tabela(f"Execução por eixo em {ano}", ["Eixo", "Indicadores", "Avaliados", "Alcance médio"], linhas,
               num={1, 2, 3}, larg=[3.4, 1, 1, 1.2], fonte="pls_execucao (conjunto núcleo)")


def detalhe_compras(doc: Doc, d: Dados, codigo: str):
    ano = d.ano
    anos = [a for a in (ano - 2, ano - 1, ano)]
    if codigo == "N10" and not d.compras.empty:
        c = d.compras[d.compras["ano"].isin(anos)]
        tab = c.groupby(["nivel_sustentabilidade", "ano"]).size().unstack(fill_value=0).reindex(columns=anos, fill_value=0)
        ordem = [k for k in NIVEL_ROT if k in tab.index]
        doc.tabela("Contratações da UFPB publicadas no PNCP, pelo tratamento da sustentabilidade nos documentos",
                   ["Nível", *map(str, anos)], [[NIVEL_ROT[k], *tab.loc[k].tolist()] for k in ordem],
                   num={1, 2, 3}, larg=[3, 1, 1, 1],
                   fonte="PNCP e Compras.gov.br; leitura dos editais, termos de referência e ETPs pelo painel")
        c_ano = c[c["ano"] == ano]
        crit = c_ano[c_ano["nivel_sustentabilidade"] == "especifico"]["criterios"].explode().value_counts().head(6)
        if not crit.empty:
            doc.p(f"Critérios obrigatórios mais frequentes em {ano}: "
                  + "; ".join(f"{k.lower()} ({v})" for k, v in crit.items()) + ".")
    if codigo == "N11" and not d.compartilhadas.empty:
        s = d.compartilhadas[d.compartilhadas["ano"].isin(anos)]
        tab = s.groupby(["tipo", "ano"]).size().unstack(fill_value=0).reindex(columns=anos, fill_value=0)
        doc.tabela("Compras compartilhadas por tipo", ["Tipo", *map(str, anos)],
                   [[t, *tab.loc[t].tolist()] for t in tab.index], num={1, 2, 3}, larg=[3, 1, 1, 1],
                   fonte="Compras.gov.br (atas de registro de preços) e PNCP (contratos)")
    if codigo == "N12" and not d.pagamentos.empty:
        p = d.pagamentos[d.pagamentos["ano"].isin(anos)]
        tab = p.groupby(["subtema", "ano"])["valor"].sum().unstack(fill_value=0).reindex(columns=anos, fill_value=0)
        tot = tab.sum()
        linhas = [[k, *[f"{mi(tab.loc[k, a])} · {pct(100 * tab.loc[k, a] / tot[a], 0) if tot[a] else '—'}"
                        for a in anos]] for k in tab.sort_values(ano, ascending=False).index]
        linhas.append(["Total pago a pessoas jurídicas", *[mi(tot[a]) for a in anos]])
        doc.tabela("Pagamentos a fornecedores pessoa jurídica por porte e localização", ["Categoria", *map(str, anos)],
                   linhas, num={1, 2, 3}, larg=[2.6, 1.3, 1.3, 1.3],
                   fonte="Portal da Transparência (pagamentos) e Cadastro Nacional da Pessoa Jurídica (Receita Federal)")


def secao_eixos(doc: Doc, d: Dados):
    ano = d.ano
    anos = [ano - 2, ano - 1, ano]
    doc.h1("Resultados por eixo")
    doc.p(f"Para cada eixo, a tabela traz a série dos indicadores do núcleo de {anos[0]} a {ano}, a meta e a faixa "
          f"no exercício. Valores marcados com * são de ano ainda incompleto. Os comentários são leituras "
          f"automáticas dos números; a análise das causas cabe à Comissão e aos setores responsáveis.")
    ind = d.ind_ano(ano)
    for e in ORDEM_EIXOS:
        sub = d.nucleo[d.nucleo["eixo_pls"] == e]
        if sub.empty:
            continue
        doc.h2(f"{'Eixo ' + e if e != 'transversal' else 'Transversal'}: {d.nome_eixo(e)}")
        if e in d.eixos.index:
            doc.p(d.eixos.loc[e, "descricao"] + ".")
        linhas = []
        for r in sub.itertuples():
            cels = []
            for a in anos:
                v, completo = d.valor(r.codigo, a)
                cels.append(num(v, r.unidade) + ("*" if not vazio(v) and completo is False else ""))
            info = ind.loc[r.codigo] if r.codigo in ind.index else None
            meta = r.meta or "—"
            linhas.append([f"{r.codigo} {r.indicador}", r.unidade, *cels, meta,
                           fx(info["faixa"] if info is not None else "sem_meta")])
        doc.tabela(f"Indicadores do núcleo · {d.nome_eixo(e)}",
                   ["Indicador", "Unidade", *map(str, anos), "Meta", f"Faixa {ano}"], linhas,
                   num={2, 3, 4}, larg=[2.8, 1.1, 1.1, 1.1, 1.1, 1.3, 1.3])
        doc.lista([comentario(d, r, ano, ind.loc[r.codigo] if r.codigo in ind.index else None)
                   for r in sub.itertuples()])
        for r in sub.itertuples():
            detalhe_compras(doc, d, r.codigo)
        doc.pendente(f"Análise da Comissão para o eixo: causas dos resultados, fatores que ajudaram ou atrapalharam "
                     f"e ajustes propostos para {ano + 1}.")


def evidencia(txt: str) -> str:
    """'consumo_m3: ultimo mes...' / 'empenhado_itens (Lampadas LED): ...' -> texto sem o nome interno da metrica"""
    return re.sub(r"^[a-z0-9_]+(?: \((.+?)\))?:", lambda m: (m.group(1) or "dados do painel") + ":", txt)


def secao_acoes(doc: Doc, d: Dados):
    doc.h1("Plano de ações")
    a = d.acoes
    if a.empty:
        doc.pendente("O plano de ações ainda não foi carregado no painel (módulo acoes).")
        return
    ref = data_br(d.data_ref)
    cont = a["situacao"].value_counts()
    doc.p(f"O PLS tem {len(a)} ações com responsável e prazo. A situação abaixo é a posição do painel em {ref}: "
          f"combina o que os setores informaram no formulário de acompanhamento com o que o painel consegue "
          f"verificar sozinho (por exemplo, se o consumo de água continua sendo medido todo mês). O índice de "
          f"cumprimento (N15) está em **{pct(a['indice_cumprimento'].iloc[0])}**.")
    doc.tabela(f"Ações do PLS por situação em {ref}", ["Situação", "Ações"],
               [[ACAO_ROT.get(k, k), int(v)] for k, v in cont.items()], num={1}, larg=[3, 1])
    tab = a.groupby(["eixo_pls", "situacao"]).size().unstack(fill_value=0)
    cols = [c for c in cont.index if c in tab.columns]
    linhas = [[f"{'Eixo ' + e if e in d.eixos.index else 'Transversal'}", *[int(tab.loc[e, c]) for c in cols]]
              for e in ORDEM_EIXOS if e in tab.index]
    doc.tabela("Ações por eixo e situação", ["Eixo", *[ACAO_ROT.get(c, c) for c in cols]], linhas,
               num=set(range(1, len(cols) + 1)), larg=[1.4, *[1] * len(cols)])
    venc = a[a["situacao"].isin(["vencida_sem_informacao", "atrasada"])].sort_values("fim")
    if not venc.empty:
        doc.h2("Ações com prazo vencido")
        doc.p(f"{len(venc)} ações passaram do prazo previsto no plano sem registro de conclusão. Isso não quer dizer "
              f"que não foram feitas: pode faltar só o registro. O responsável deve informar a situação ou propor "
              f"novo prazo.")
        doc.tabela("Ações com prazo vencido", ["Ação", "Responsável", "Prazo", "Situação"],
                   [[f"{r.id} {r.acao}", r.responsavel, f"{r.fim[5:]}/{r.fim[:4]}", ACAO_ROT.get(r.situacao, r.situacao)]
                    for r in venc.itertuples()], larg=[4, 1.6, 0.8, 1.4])
    verif = a[a["verificada_painel"] & (a["evidencia_painel"] != "")]
    if not verif.empty:
        doc.h2("Ações verificadas pelos dados do painel")
        doc.lista([f"**{r.id}** {r.acao} — {evidencia(r.evidencia_painel)}" for r in verif.itertuples()])
    doc.h2("Relato dos responsáveis")
    reg = d.acomp[d.acomp.get("situacao", pd.Series(dtype=str)) != ""] if not d.acomp.empty else d.acomp
    if reg.empty:
        doc.pendente("Nenhum setor registrou ainda o acompanhamento das ações no formulário do painel. Com os "
                     "registros, esta parte traz as justificativas, os facilitadores, as dificuldades e os ajustes "
                     "propostos por ação.")
    else:
        nomes = a.set_index("id")["acao"]
        for r in reg.sort_values("acao_id").itertuples():
            partes = [f"situação informada: {r.situacao.replace('_', ' ')}"]
            for campo, rot in (("justificativa", "justificativa"), ("facilitadores", "facilitadores"),
                               ("dificuldades", "dificuldades"), ("ajuste_sugerido", "ajuste proposto")):
                v = getattr(r, campo, "")
                if v:
                    partes.append(f"{rot}: {v}")
            doc.p(f"**{r.acao_id} {nomes.get(r.acao_id, '')}** ({r.ciclo}) — " + "; ".join(partes) + ".")
    sem = a[a["situacao"].isin(["sem_informacao", "vencida_sem_informacao"])]["responsavel"].value_counts().head(8)
    if not sem.empty:
        doc.p("Responsáveis com mais ações sem registro: " + "; ".join(f"{k} ({v})" for k, v in sem.items()) + ".")


def secao_ano_corrente(doc: Doc, d: Dados):
    atual = d.ano + 1
    g = d.geral(atual)
    if g is None:
        return
    doc.h1(f"Posição parcial de {atual}")
    doc.p(f"Até {data_br(d.data_ref)}, o índice sintético de {atual} está em **{pct(g['indice_sintetico'])}**. "
          f"Como as metas só são avaliadas com o ano fechado, o componente de metas repete o alcance de "
          f"{int(g['ano_metas']) if not vazio(g['ano_metas']) else d.ano} ({pct(g['indice_metas_usado'])}) e o de ações "
          f"usa o cumprimento atual do plano ({pct(g['indice_acoes'])}). O número é uma prévia e muda a cada ciclo de "
          f"acompanhamento.")


def achados(doc: Doc, d: Dados):
    ano = d.ano
    doc.h1("Achados e recomendações")
    doc.p("Os pontos abaixo saem do cruzamento automático dos dados. A Comissão decide quais entram na versão final "
          "e em que termos.")
    itens = []
    sem_meta = d.nucleo[d.nucleo["tipo_meta"] == "acompanhamento"]
    if not sem_meta.empty:
        itens.append(f"**Metas.** {len(sem_meta)} dos {len(d.nucleo)} indicadores do núcleo ainda não têm meta, o que "
                     f"limita o índice sintético. Recomendação: fixar metas para "
                     + ", ".join(sem_meta["codigo"]) + ", partindo das sugestões do Anexo A.")
    grandes = []
    for r in d.nucleo.itertuples():
        v, c = d.valor(r.codigo, ano)
        va, ca = d.valor(r.codigo, ano - 1)
        if not vazio(v) and not vazio(va) and va and c and ca and abs(100 * (v - va) / abs(va)) > LIMITE_VARIACAO:
            grandes.append(f"{r.codigo} {r.indicador.lower()} ({pct(100 * (v - va) / abs(va), 0)})")
    if grandes:
        itens.append(f"**Variações fortes de {ano - 1} para {ano}.** " + "; ".join(grandes) + ". Recomendação: "
                     "conferir com os setores responsáveis se a variação é real ou efeito de medição ou faturamento "
                     "antes de publicar o resultado.")
    if not d.acoes.empty:
        venc = int((d.acoes["situacao"] == "vencida_sem_informacao").sum())
        sem = int((d.acoes["situacao"] == "sem_informacao").sum())
        if venc or sem:
            itens.append(f"**Acompanhamento das ações.** {venc} ações com prazo vencido e {sem} em curso estão sem "
                         f"registro. Recomendação: cobrar dos responsáveis o preenchimento do formulário de "
                         f"acompanhamento a cada semestre e rever os prazos que não serão cumpridos.")
    if not d.compras.empty:
        c = d.compras[d.compras["ano"] == ano]
        mk = c["marcadores"].map(lambda x: set(x) if x is not None else set())
        alim = mk.map(lambda s: "alimentos" in s)
        sem_af = int((alim & ~mk.map(lambda s: "agricultura_familiar" in s)).sum())
        if alim.any() and sem_af:
            itens.append(f"**Agricultura familiar.** {sem_af} de {int(alim.sum())} contratações de alimentos de {ano} "
                         f"não trazem cláusula de compra da agricultura familiar. Recomendação: incluir a reserva "
                         f"nos termos de referência de gêneros alimentícios.")
        pref = int((c["nivel_sustentabilidade"] == "preferencial").sum())
        gen = int(c["nivel_sustentabilidade"].isin(["generico", "nenhum"]).sum())
        if pref or gen:
            itens.append(f"**Critérios de sustentabilidade nos editais.** Em {ano}, {pref} contratações só tinham "
                         f"cláusula de preferência (“preferencialmente”) e {gen} só menção genérica ou nenhuma. "
                         f"Recomendação: orientar as UASGs a transformar as cláusulas-padrão em exigências "
                         f"verificáveis, conforme o Guia Nacional de Contratações Sustentáveis da AGU.")
    informados = d.nucleo[(d.nucleo["automacao"] != "automatizado")]
    falta = [r for r in informados.itertuples() if vazio(d.valor(r.codigo, ano)[0])]
    if falta:
        itens.append("**Indicadores sem fonte automática.** " + "; ".join(
            f"{r.codigo} {r.indicador.lower()}: {(r.hoje or r.observacao or 'informar pelo formulário').rstrip('.')}"
            for r in falta) + ".")
    if not d.saude.empty:
        at = d.saude[d.saude["nivel"].isin(["erro", "atencao"])]
        if not at.empty:
            itens.append("**Qualidade dos dados.** A verificação automática da carga apontou: "
                         + "; ".join(t.rstrip(".") for t in at["titulo"]) + ". Detalhe no Anexo B.")
    doc.lista(itens)
    doc.pendente("Recomendações da Comissão e encaminhamentos para o próximo exercício.")


def anexos(doc: Doc, d: Dados):
    doc.h1("Anexo A – Fichas dos indicadores do núcleo", anexo=True)
    doc.p(f"A construção detalhada de cada indicador, com as fontes, os filtros e os limites conhecidos, está em "
          f"{FICHAS}.")
    doc.tabela("Indicadores do núcleo do PLS", ["Código", "Indicador e fórmula", "Fonte", "Coleta", "Meta"],
               [[r.codigo, f"**{r.indicador}** ({r.unidade}): {r.formula}", r.fonte,
                 AUTOMACAO_ROT.get(r.automacao, r.automacao),
                 r.meta or (f"Sem meta. Sugestão: {r.meta_sugerida}" if r.meta_sugerida else "Sem meta")]
                for r in d.nucleo.itertuples()], larg=[0.6, 2.6, 2.2, 1, 1.6])
    doc.h1("Anexo B – Situação da carga de dados", anexo=True)
    if d.saude.empty:
        doc.p("A verificação da carga ainda não rodou.")
        return
    rot = {"erro": "Erro", "atencao": "Atenção", "info": "Informação", "ok": "Em dia"}
    ordem = {"erro": 0, "atencao": 1, "info": 2, "ok": 3}
    s = d.saude.assign(o=d.saude["nivel"].map(ordem)).sort_values("o")
    doc.p(f"Verificação automática feita após a carga de {data_br(s['data_referencia'].iloc[0])}.")
    doc.tabela("Verificações da carga de dados", ["Situação", "Verificação", "O que fazer"],
               [[rot.get(r.nivel, r.nivel), r.titulo, r.acao_sugerida or "—"] for r in s.itertuples()],
               larg=[0.9, 2.6, 3])


def montar(ano: int) -> tuple[Doc, dict]:
    d = Dados(ano)
    doc = Doc()
    secao_apresentacao(doc, d)
    secao_metodologia(doc, d)
    secao_visao_geral(doc, d)
    secao_eixos(doc, d)
    secao_acoes(doc, d)
    secao_ano_corrente(doc, d)
    achados(doc, d)
    doc.h1("Pendências para fechar o relatório")
    doc.lista(["Completar os blocos “A preencher” (Comissão, análise por eixo, recomendações).",
               "Validar os números com os setores responsáveis, em especial as variações fortes apontadas na seção 7.",
               "Fixar as metas que faltam e confirmar os pesos do índice sintético e os limites das faixas.",
               "Aprovar a versão final na Comissão Gestora e publicar no site da UFPB."])
    anexos(doc, d)
    gerado = data_br(d.data_ref)
    meta = {"titulo": f"Relatório Anual do PLS UFPB {ano}",
            "eyebrow": f"UFPB · Comissão Gestora do PLS · Exercício {ano}",
            "h1": "Relatório de Avaliação de Desempenho do PLS UFPB 2025–2029", "subtitulo": f"Exercício {ano}",
            "lead": f"Resultados dos indicadores do núcleo, execução do plano de ações, achados e recomendações do "
                    f"exercício de {ano}, a partir dos dados do Painel de Sustentabilidade.",
            "selo": f"Minuta gerada pelo painel em {gerado} · trechos a preencher pela Comissão",
            "nota_capa": f"Minuta gerada pelo Painel de Sustentabilidade em {gerado}. Os trechos destacados em amarelo "
                         f"devem ser completados pela Comissão antes da aprovação.",
            "rodape_doc": f"PLS UFPB · Relatório anual {ano} · minuta",
            "rodape_html": f'Painel de Sustentabilidade da UFPB · <a href="{PAINEL}" target="_blank" rel="noopener">'
                           f"painel do núcleo do PLS</a>. A versão editável deste relatório (Word) é gerada junto "
                           f"com esta página."}
    return doc, meta


# ------------------------------------------------------------------ main

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--ano", type=int, default=date.today().year - 1, help="exercício (padrão: último ano fechado)")
    ap.add_argument("--saida", type=Path, default=Path(__file__).parent)
    a = ap.parse_args(argv)
    doc, meta = montar(a.ano)
    a.saida.mkdir(parents=True, exist_ok=True)
    arq_html = a.saida / f"relatorio_pls_{a.ano}.html"
    arq_docx = a.saida / f"relatorio_pls_{a.ano}.docx"
    arq_html.write_text(html_doc(doc, meta), encoding="utf-8")
    docx_doc(doc, meta, arq_docx)
    print(f"{arq_html}\n{arq_docx}\n{doc.n_sec} seções, {doc.n_tab} tabelas, "
          f"{sum(b['t'] == 'pendente' for b in doc.blocos)} trechos a preencher")


if __name__ == "__main__":
    main()
