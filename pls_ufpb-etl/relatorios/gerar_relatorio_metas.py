"""Relatorio de automacao das metas do PLS 2025-2029 -> Word (paisagem) e HTML.

    python relatorios/gerar_relatorio_metas.py [--saida DIR]

Para cada meta do plano (34, ref/indicadores_pls.csv com id E*): se ja e
automatica, como foi automatizada, a forma de calculo, se precisa de
aprimoramento e como (ref/metas_aprimoramento.csv). O ultimo valor e a
situacao vem de data/processed/pls_metas.parquet. Anexo: os indicadores de
acompanhamento do painel (id A*), que nao tem meta.
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
from common.storage import load_processed  # noqa: E402
from relatorios.blocos import Doc, docx_doc, html_doc  # noqa: E402

AUTOMACAO = {"automatico": ("Sim", "atingida"), "integracao": ("Não · integração", "progresso"),
             "informado": ("Não · informado", "sem_meta")}
PRIORIDADE = {"alta": ("Sim · prioridade alta", "distante"), "media": ("Sim · prioridade média", "progresso"),
              "baixa": ("Sim · prioridade baixa", "proxima")}
SITUACAO = {"atingida": "meta atingida", "nao_atingida": "meta não atingida", "em_andamento": "em andamento",
            "linha_de_base": "linha de base", "historico": "antes da linha de base", "acompanhamento": "acompanhamento"}
FONTE = {"publica": "dados públicos", "fornecedor": "dados do fornecedor", "interna": "sistema interno da UFPB",
         "documental": "registro documental"}


def _num(v: float, casas: int = 1) -> str:
    return f"{v:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def valor_fmt(v: float, unidade: str) -> str:
    if unidade.startswith("R$"):
        return f"R$ {_num(v, 0)}"
    if unidade == "%":
        return f"{_num(v)}%"
    if unidade == "kg CO2e" and abs(v) >= 1000:
        return f"{_num(v / 1000)} t CO2e"
    casas = 0 if abs(v) >= 1000 or float(v).is_integer() else 1 if abs(v) >= 1 else 2
    return f"{_num(v, casas)} {unidade}"


class Dados:
    def __init__(self):
        self.cat = pd.read_csv(config.REF_DIR / "indicadores_pls.csv", sep=";", dtype=str, keep_default_na=False)
        self.apr = pd.read_csv(config.REF_DIR / "metas_aprimoramento.csv", sep=";", dtype=str,
                               keep_default_na=False).set_index("id")
        self.eixos = pd.read_csv(config.REF_DIR / "eixos_pls.csv", sep=";", dtype=str).set_index("eixo_pls")["eixo"]
        self.metas = load_processed("pls_metas")
        self.plano = self.cat[self.cat["id"].str.startswith("E")]
        self.amplia = self.cat[self.cat["id"].str.startswith("A")]
        faltam = set(self.plano["id"]) - set(self.apr.index)
        assert not faltam, f"metas sem avaliacao em ref/metas_aprimoramento.csv: {faltam}"

    def ultimo(self, ind_id: str) -> str:
        """Ultimo ano completo com valor (ou o parcial, se so houver ele) e a situacao."""
        m = self.metas[(self.metas["indicador_id"] == ind_id) & self.metas["valor"].notna()] if not self.metas.empty else []
        if len(m) == 0:
            return "sem valor apurado ainda"
        m = m.sort_values("ano")
        comp = m[m["ano_completo"] == True]  # noqa: E712
        r = (comp if len(comp) else m).iloc[-1]
        un = self.cat.set_index("id").at[ind_id, "unidade"]
        txt = f"{int(r['ano'])}{'' if r['ano_completo'] else ' (parcial)'}: {valor_fmt(float(r['valor']), un)}"
        sit = SITUACAO.get(r.get("situacao"), "")
        return f"{txt}, {sit}" if sit and sit != "acompanhamento" else txt


def sem_prefixo(rota: str) -> str:
    r = rota.removeprefix("Automático: ").removeprefix("Automático:").strip()
    return r[:1].upper() + r[1:]


def linha_meta(d: Dados, r) -> list:
    a = d.apr.loc[r.id]
    auto_txt, auto_fx = AUTOMACAO[r.automacao]
    if r.automacao == "automatico":
        como_auto = sem_prefixo(r.rota_automacao)
    elif r.automacao == "integracao":
        como_auto = f"Ainda não. Fonte prevista: {r.rota_automacao}"
    else:
        como_auto = f"Ainda não: informado pelo setor no formulário do painel ({FONTE.get(r.tipo_fonte, r.tipo_fonte)})."
    if a["precisa_aprimorar"] == "sim":
        prec = {"txt": PRIORIDADE[a["prioridade"]][0], "fx": PRIORIDADE[a["prioridade"]][1]}
    else:
        prec = {"txt": "Não", "fx": "atingida"}
    meta_cel = (f"**{r.indicador}** ({r.id}, Tabela {r.tabela_pls}). Meta: {r.meta}. "
                f"Responsável: {r.responsavel}. Último valor: {d.ultimo(r.id)}.")
    return [meta_cel, {"txt": auto_txt, "fx": auto_fx}, como_auto, f"{r.formula} (em {r.unidade})", prec,
            a["como_aprimorar"]]


def montar() -> tuple[Doc, dict]:
    d = Dados()
    doc = Doc()
    n = len(d.plano)
    cont = d.plano["automacao"].value_counts()
    apr = d.apr.loc[d.plano["id"]]
    precisa = apr[apr["precisa_aprimorar"] == "sim"]

    doc.h1("Resumo")
    doc.p(f"O PLS UFPB 2025–2029 tem **{n} metas** nas tabelas 16 a 24, em seis eixos. Este relatório mostra, meta a meta, "
          "se o painel já apura o indicador sozinho, como faz isso, a fórmula usada e o que falta para melhorar a apuração.")
    doc.kpis([(str(n), "metas do plano"), (str(cont.get("automatico", 0)), "já automáticas"),
              (str(cont.get("integracao", 0)), "automatizáveis por integração"),
              (str(cont.get("informado", 0)), "informadas pelos setores"),
              (str(len(precisa)), "precisam de aprimoramento")])
    linhas = []
    for e, g in d.plano.groupby("eixo_pls"):
        ga = d.apr.loc[g["id"]]
        linhas.append([f"{e} · {d.eixos.get(e, '')}", str(len(g)), str((g["automacao"] == "automatico").sum()),
                       str((g["automacao"] == "integracao").sum()), str((g["automacao"] == "informado").sum()),
                       str((ga["prioridade"].eq("alta") & ga["precisa_aprimorar"].eq("sim")).sum())])
    linhas.append(["**Total**", f"**{n}**", f"**{cont.get('automatico', 0)}**", f"**{cont.get('integracao', 0)}**",
                   f"**{cont.get('informado', 0)}**",
                   f"**{(precisa['prioridade'] == 'alta').sum()}**"])
    doc.tabela("Metas por eixo e forma de apuração",
               ["Eixo", "Metas", "Automáticas", "Integração", "Informadas", "Aprimorar com prioridade alta"], linhas,
               num=(1, 2, 3, 4, 5), larg=[4, 1, 1.2, 1.2, 1.2, 1.8])

    doc.h1("Como ler as tabelas")
    doc.lista([
        "**Automático (Sim):** o painel calcula o indicador a cada carga, sem digitação, a partir de dados públicos "
        "(Portal da Transparência, SIPAC, PNCP, INEP, ENAP).",
        "**Não · integração:** a fonte existe e é conhecida, mas ainda falta ligar o painel a ela (um coletor novo ou um "
        "pedido de extração a um sistema da UFPB).",
        "**Não · informado:** o valor vem de registro do setor responsável, pelo formulário do painel. Nem toda meta "
        "informada precisa ser automatizada (registros únicos, como a implantação de uma metodologia).",
        "**Precisa aprimorar:** prioridade **alta** quando o número publicado hoje pode estar errado ou não mede o que a "
        "meta pede; **média** quando falta automatizar uma fonte disponível; **baixa** para ajustes de conferência.",
        "**Último valor:** o último ano completo apurado e a situação da meta nesse ano (o ano em curso só aparece "
        "quando é o único com valor).",
    ])

    cab = ["Meta", "Automático", "Como foi automatizado", "Forma de cálculo", "Precisa aprimorar?", "Como aprimorar"]
    larg = [4.2, 1.9, 4.1, 3.3, 1.8, 5.0]
    for e, g in d.plano.groupby("eixo_pls"):
        doc.h1(f"Eixo {e} · {d.eixos.get(e, '')}", quebra=True)
        doc.tabela(f"Metas do eixo {e}", cab, [linha_meta(d, r) for r in g.itertuples()], larg=larg,
                   fonte="catálogo do painel (ref/indicadores_pls.csv), avaliação em ref/metas_aprimoramento.csv e "
                         "valores de data/processed/pls_metas.parquet")

    doc.h1("Prioridades", quebra=True)
    doc.p("Metas com aprimoramento de prioridade alta, em que o número publicado hoje pode estar errado ou não mede o que "
          "a meta pede:")
    alta = precisa[precisa["prioridade"] == "alta"]
    cat = d.cat.set_index("id")
    doc.lista([f"**{cat.at[i, 'indicador']}** ({i}): {r['como_aprimorar']}" for i, r in alta.iterrows()])
    doc.p("Ganhos rápidos, com fonte pública já identificada e sem depender de outro setor:")
    rapidos = ["E1-AVN-01", "E1-CONTRATA-01", "E2-LEILAO-01", "E4-PATENTE-01", "E1-RU-02"]
    doc.lista([f"**{cat.at[i, 'indicador']}** ({i})" for i in rapidos if i in cat.index])
    doc.p("Dependem de extração agregada de sistemas internos (SIGRH e patrimônio), no mesmo formato do pedido de dados "
          "de estudantes à STI: E3-PATRIM-01, E4-CAPAC-01, E5-DOACAO-01, E6-CAPAC-01, E6-CAPAC-03 e E6-CAPAC-04.")

    doc.h1("Indicadores de acompanhamento do painel", anexo=True, quebra=True)
    doc.p(f"Além das metas do plano, o painel acompanha **{len(d.amplia)} indicadores sem meta** (ampliações), que dão "
          "contexto às metas, como gastos em R$ constantes, emissões e intensidades por m².")
    doc.tabela("Indicadores de acompanhamento", ["Indicador", "Automático", "Como é apurado", "Forma de cálculo"],
               [[f"**{r.indicador}** ({r.id}). Último valor: {d.ultimo(r.id)}.",
                 {"txt": AUTOMACAO[r.automacao][0], "fx": AUTOMACAO[r.automacao][1]},
                 sem_prefixo(r.rota_automacao), f"{r.formula} (em {r.unidade})"] for r in d.amplia.itertuples()],
               larg=[5.5, 1.9, 6.8, 5.8])

    hoje = date.today().strftime("%d/%m/%Y")
    meta = {"titulo": "Automação das Metas do PLS", "eyebrow": "UFPB · Painel de Sustentabilidade",
            "h1": "Automação das metas do PLS 2025–2029",
            "subtitulo": "Situação de cada meta: automação, cálculo e aprimoramentos",
            "lead": f"As {n} metas do plano, com a forma de apuração, a fórmula e o que melhorar em cada uma.",
            "selo": f"Versão de {hoje}",
            "nota_capa": f"Relatório gerado pelo Painel de Sustentabilidade da UFPB em {hoje}, a partir do catálogo de "
                         "indicadores e dos valores apurados na última carga.",
            "rodape_doc": "Automação das metas do PLS 2025–2029", "rodape_html": "", "toc_niveis": 1,
            "paisagem": True}
    return doc, meta


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--saida", type=Path, default=Path(__file__).parent)
    a = ap.parse_args(argv)
    doc, meta = montar()
    a.saida.mkdir(parents=True, exist_ok=True)
    arq_html, arq_docx = a.saida / "automacao_metas_pls.html", a.saida / "automacao_metas_pls.docx"
    arq_html.write_text(html_doc(doc, meta), encoding="utf-8")
    docx_doc(doc, meta, arq_docx)
    print(arq_html)
    print(arq_docx)


if __name__ == "__main__":
    main()
