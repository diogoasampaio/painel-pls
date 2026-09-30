"""Pagina com tres abas: indicadores do PLS automatizados x nao automatizados,
com descricao, formula e (nos automatizados) os valores calculados pelo ETL;
e as variaveis usadas nas contas (numeradores e denominadores), ano a ano."""

import html
import math
import sys
from datetime import date
from pathlib import Path

import pandas as pd

ETL = Path(r"C:\Users\diogo\repositorios\codeinfo\sustentabilidade\pls_ufpb-etl")
OUT = Path(__file__).with_name("indicadores_pls_ufpb.html")
RELATORIO = "https://claude.ai/artifact/WzARzGDgoTKjA8GNNhCbu7"
e = html.escape

cat = pd.read_csv(ETL / "ref" / "indicadores_pls.csv", sep=";", dtype=str, keep_default_na=False)
eixos = pd.read_csv(ETL / "ref" / "eixos_pls.csv", sep=";", dtype=str).set_index("eixo_pls")["eixo"]
metas = pd.read_parquet(ETL / "data" / "processed" / "pls_metas.parquet")
metas = metas[metas["ano"].between(2023, 2026)]
ind = pd.read_parquet(ETL / "data" / "processed" / "pls_indicadores.parquet")
comunidade = pd.read_parquet(ETL / "data" / "processed" / "pls_comunidade.parquet")
ipca = pd.read_parquet(ETL / "data" / "processed" / "pls_ipca.parquet")
area = pd.read_csv(ETL / "ref" / "area_construida.csv", sep=";", dtype={"area_m2": float})
sys.path.insert(0, str(ETL))
from metas import catalogo  # noqa: E402

SITUACAO = {
    "atingida": ("ok", "Meta atingida"), "nao_atingida": ("ruim", "Meta não atingida"),
    "em_andamento": ("neutro", "Em andamento"), "linha_de_base": ("base", "Linha de base"),
    "acompanhamento": ("base", "Acompanhamento"), "historico": ("base", "Histórico"),
}
NIVEL = {
    ("integracao", "publica"): ("pub", "Integrar dado público"),
    ("integracao", "fornecedor"): ("forn", "Integrar dado do fornecedor"),
    ("integracao", "interna"): ("int", "Integrar sistema da UFPB"),
    ("informado", "documental"): ("inf", "Informado pela Comissão"),
}


def num(v: float, unidade: str) -> str:
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "—"
    casas = 0 if abs(v) >= 100 or v == 0 else (1 if abs(v) >= 10 else 2)
    s = f"{v:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    if unidade.startswith("R$"):
        return "R$ " + s + unidade[2:]
    return f"{s} {unidade}".strip()


def valores(ind_id: str, unidade: str) -> str:
    m = metas[metas["indicador_id"] == ind_id].sort_values("ano")
    if m.empty:
        return '<p class="sem">Sem valor calculado ainda.</p>'
    cels = []
    for r in m.itertuples():
        cls, rot = SITUACAO.get(r.situacao, ("base", r.situacao))
        parcial = "" if r.ano_completo else '<span class="parcial">parcial</span>'
        var = ""
        if isinstance(r.variacao_pct, float) and not math.isnan(r.variacao_pct):
            var = f'<span class="var">{r.variacao_pct:+.1f}%'.replace(".", ",") + " sobre o ano de referência</span>"
        nominal = ""
        if isinstance(r.valor_nominal, float) and not math.isnan(r.valor_nominal):
            nominal = (f'<span class="nominal">Nominal <span class="num">{e(num(r.valor_nominal, unidade))}</span></span>')
        cels.append(
            f'<div class="ano"><span class="a">{r.ano}{parcial}</span><b class="num">{e(num(r.valor, unidade))}</b>'
            f'{nominal}<span class="sit {cls}">{rot}</span>{var}</div>'
        )
    corrigido = m["ref_ipca"].dropna()
    nota = ""
    if len(corrigido):
        a, mes = corrigido.iloc[0].split("-")
        nota = (f'<p class="nota-ipca">Valor em destaque: R$ de {mes}/{a}, corrigido pelo IPCA mês a mês. '
                f'“Nominal” é a soma dos valores como foram pagos, para conferência com o Portal e o Tesouro Gerencial.</p>')
    return f'<div class="anos">{"".join(cels)}</div>{nota}'


def cartao(r: pd.Series, automatizado: bool) -> str:
    plano = r["id"].startswith("E")
    origem = f'PLS · Tabela {e(r["tabela_pls"])}' if plano and r["tabela_pls"] else "Ampliação do painel"
    meta = f'<div class="kv"><dt>Meta</dt><dd>{e(r["meta"])}</dd></div>' if r["meta"] else ""
    if automatizado:
        chip = '<span class="chip auto">Automatizado</span>'
        como = f'<div class="kv"><dt>Fonte</dt><dd>{e(r["rota_automacao"] or r["fonte_hoje"])}</dd></div>'
        extra = valores(r["id"], r["unidade"])
    else:
        cls, rot = NIVEL.get((r["automacao"], r["tipo_fonte"]), ("inf", "Informado pela Comissão"))
        chip = f'<span class="chip {cls}">{rot}</span>'
        como = (f'<div class="kv"><dt>Hoje</dt><dd>{e(r["fonte_hoje"] or "Não há")}</dd></div>'
                f'<div class="kv"><dt>Caminho</dt><dd>{e(r["rota_automacao"])}</dd></div>')
        extra = ""
    conf = f'<p class="confirmar"><b>A confirmar:</b> {e(r["confirmar"])}</p>' if r["confirmar"] else ""
    ficha = f'<a class="ficha" href="{RELATORIO}#{e(r["id"])}" target="_blank" rel="noopener">Como este indicador é construído →</a>'
    busca = " ".join([r["id"], r["indicador"], r["objetivo"], r["formula"], r["responsavel"]]).lower()
    return (
        f'<article class="ind" data-eixo="{r["eixo_pls"]}" data-busca="{e(busca)}">'
        f'<header><span class="id num">{e(r["id"])}</span><span class="origem">{origem}</span>{chip}</header>'
        f'<h3>{e(r["indicador"])}</h3>'
        f'<p class="desc">{e(r["objetivo"])}</p>'
        f'<div class="formula"><span>Fórmula</span><code>{e(r["formula"])}</code><em>{e(r["unidade"])}</em></div>'
        f'<dl>{meta}{como}<div class="kv"><dt>Responsável</dt><dd>{e(r["responsavel"])}</dd></div></dl>'
        f'{conf}{extra}{ficha}</article>'
    )


def aba(df: pd.DataFrame, automatizado: bool) -> str:
    partes = []
    for eixo in sorted(df["eixo_pls"].unique(), key=int):
        sub = df[df["eixo_pls"] == eixo]
        plano, ampl = (sub["id"].str.startswith("E")).sum(), (sub["id"].str.startswith("A")).sum()
        cont = f"{plano} do plano" + (f" · {ampl} de ampliação" if ampl else "")
        partes.append(
            f'<section class="eixo" data-eixo="{eixo}"><h2><span class="n">Eixo {eixo}</span> {e(eixos[eixo])}'
            f'<small>{cont}</small></h2><div class="grade">'
            + "".join(cartao(r, automatizado) for _, r in sub.iterrows()) + "</div></section>"
        )
    return "".join(partes)


auto = cat[cat["automacao"] == "automatico"]
pend = cat[cat["automacao"] != "automatico"]
plano = cat[cat["id"].str.startswith("E")]
n_auto_plano = int((plano["automacao"] == "automatico").sum())
botoes_eixo = "".join(
    f'<button type="button" data-eixo="{k}" aria-pressed="false">Eixo {k}</button>' for k in sorted(cat["eixo_pls"].unique(), key=int)
)

# ------------------------------------------------------------ aba de variaveis

ANOS = [2023, 2024, 2025, 2026]
METRICA = {
    "consumo_kwh": ("Energia elétrica consumida", "kWh", "Faturas da Energisa nos processos de pagamento (SIPAC): kWh medido por unidade consumidora, somado por campus e mês de referência."),
    "consumo_m3": ("Água consumida", "m³", "Faturas agrupadas da CAGEPA nos processos de pagamento (SIPAC): m³ medido por ligação, somado por campus e mês de referência."),
    "consumo_litros": ("Combustível abastecido pela frota", "L", "Relatórios de abastecimento da gerenciadora de frota (GOLDI até mai/2024, PRIME depois) nos processos de pagamento (SIPAC), por data do abastecimento."),
    "residuos_kg": ("Resíduos de saúde coletados (grupos A, B e E)", "kg", "Relatório de fiscalização mensal da GMA/SINFRA nos processos de pagamento da B-Green/Stericycle (SIPAC)."),
    "co2e_kg": ("Emissões das viagens aéreas a serviço", "kg CO2e", "Trechos aéreos das viagens realizadas (Portal da Transparência) × fator de emissão da ferramenta GHG Protocol."),
    "pago": ("Despesa paga", "R$", "Arquivos diários de despesas do Portal da Transparência: pagamentos do ano mais restos a pagar pagos, por natureza de despesa."),
    "pago_acao": ("Despesa paga numa ação orçamentária do PLS", "R$", "Arquivos diários de despesas do Portal da Transparência: pagamentos cujo empenho é da ação 4572 (Capacitação de servidores), todas as naturezas; a ação vem do empenho."),
    "emissoes_kgco2e": ("Emissões de gases de efeito estufa", "kg CO2e", "Frota (litros × fator fóssil, sem a mistura de biocombustível), energia da rede (kWh × fator do SIN) e viagens aéreas. Fatores em ref/fatores_gee.csv."),
    "empenhado_material_consumo": ("Material de consumo empenhado", "R$", "Itens de material de consumo (3.3.90.30) das notas de empenho, separados em com e sem atributo sustentável."),
    "evg_certificados": ("Certificações na Escola Virtual de Governo", "un", "Matrículas concluídas em cursos da EVG/ENAP por pessoas que declaram a UFPB como instituição, pelo mês da matrícula (arquivos bimestrais do dados.gov.br)."),
    "evg_pessoas_sust": ("Pessoas certificadas em sustentabilidade na EVG", "pessoas", "Pessoas distintas (código anonimizado) que declaram a UFPB e concluíram no ano curso de sustentabilidade na EVG, contadas no mês da primeira certificação."),
    "empenhado_itens": ("Valor empenhado em itens identificados pelo texto", "R$", "Itens das notas de empenho (Portal da Transparência) cuja descrição casa com as regras de texto do painel (copos, LED, solar, atributo sustentável)."),
}
N_VARS = [0]


def _uso_por_metrica() -> dict:
    """metrica -> {subtema: [ids]} (tema=... expande nos subtemas do tema)."""
    uso: dict[str, dict[str, list[str]]] = {}
    for r in cat[cat["automacao"] == "automatico"].itertuples():
        calc = catalogo.parse_calculo(r.calculo)
        if not calc or calc["tipo"] != "ind":
            continue
        sel = ind[ind["metrica"] == calc["metrica"]]
        if calc["tema"]:
            sel = sel[sel["tema_codigo"] == calc["tema"]]
        subs = set(calc["subtemas"] or sel["subtema"].unique()) | set(calc.get("razao_subtemas") or [])
        for sub in subs:
            uso.setdefault(calc["metrica"], {}).setdefault(sub, []).append(r.id)
    return uso


def _meses(metrica: str) -> dict:
    fonte = "pago" if metrica in ("empenhado_itens", "pago_acao", "empenhado_material_consumo") else ("evg_matriculas" if metrica.startswith("evg_") else metrica)
    return ind[ind["metrica"] == fonte].groupby("ano")["mes"].nunique().to_dict()


def _celula(nom: float, real: float, unidade: str) -> str:
    if unidade == "R$" and not math.isnan(real):
        return (f'<td class="r"><span class="num">{e(num(nom, unidade))}</span>'
                f'<small class="corr">corrigido {e(num(real, unidade))}</small></td>')
    return f'<td class="r num">{e(num(nom, unidade))}</td>'


def _card_metrica(metrica: str, usos: dict[str, list[str]]) -> str:
    nome, unidade, fonte = METRICA.get(metrica, (metrica, "", ""))
    sel = ind[(ind["metrica"] == metrica) & ind["subtema"].isin(usos) & ind["ano"].isin(ANOS)]
    g = sel.groupby(["subtema", "ano"])[["valor_nominal", "valor_real"]].sum()
    meses = _meses(metrica)
    cab = "".join(f'<th class="r">{a}<small>{meses.get(a, 0)} meses</small></th>' for a in ANOS)
    linhas = []
    for sub in sorted(usos):
        ids = ", ".join(sorted(set(usos[sub])))
        tds = "".join(
            _celula(*(g.loc[(sub, a)].tolist() if (sub, a) in g.index else [float("nan")] * 2), unidade) for a in ANOS
        )
        linhas.append(f'<tr><th scope="row">{e(sub)}<small>{e(ids)}</small></th>{tds}</tr>')
    tot = sel.groupby("ano")[["valor_nominal", "valor_real"]].sum()
    tds = "".join(_celula(*(tot.loc[a].tolist() if a in tot.index else [float("nan")] * 2), unidade) for a in ANOS)
    if len(usos) > 1:
        linhas.append(f'<tr class="total"><th scope="row">Total</th>{tds}</tr>')
    ids_todos = sorted({i for v in usos.values() for i in v})
    eixos_uso = " ".join(sorted({cat.set_index("id").loc[i, "eixo_pls"] for i in ids_todos}))
    busca = " ".join([metrica, nome, fonte, *usos, *ids_todos]).lower()
    nota_rs = ('<p class="nota-ipca">Valor como foi pago (nominal); abaixo, corrigido pelo IPCA para R$ de '
               f'{ref_ipca_txt()}.</p>') if unidade == "R$" else ""
    N_VARS[0] += 1
    return (
        f'<article class="ind var" data-eixo="{eixos_uso}" data-busca="{e(busca)}">'
        f'<header><span class="id num">{e(metrica)}</span><span class="origem">{e(unidade)}</span>'
        f'<span class="chip auto">Numerador</span></header>'
        f'<h3>{e(nome)}</h3><p class="desc">{e(fonte)}</p>'
        f'<div class="tabela-var"><table><thead><tr><th>Recorte · usado em</th>{cab}</tr></thead>'
        f'<tbody>{"".join(linhas)}</tbody></table></div>{nota_rs}</article>'
    )


def ref_ipca_txt() -> str:
    ref = ind["ref_ipca"].dropna().max()
    return f"{ref[5:]}/{ref[:4]}" if isinstance(ref, str) else "—"


def _usam(campo: str) -> list[str]:
    return sorted(r.id for r in cat[cat["automacao"] == "automatico"].itertuples() if campo in r.calculo)


def _card_comunidade() -> str:
    tab = pd.read_csv(ETL / "ref" / "comunidade_ufpb.csv", sep=";").sort_values("ano")
    inep = comunidade[comunidade["ufpb"]].set_index("ano")["comunidade"]
    usado = ind.dropna(subset=["ano_comunidade"]).groupby("ano")["ano_comunidade"].max().to_dict()
    linhas = "".join(
        f'<tr><th scope="row">{int(r.ano)}</th><td class="r num">{num(r.discentes, "")}</td>'
        f'<td class="r num">{num(r.docentes, "")}</td><td class="r num">{num(r.tecnicos, "")}</td>'
        f'<td class="r num">{num(r.terceirizados, "")}</td><td class="r num"><b>{num(r.comunidade, "")}</b></td>'
        f'<td class="r num">{num(inep.get(r.ano), "") if r.ano in inep.index else "—"}</td></tr>'
        for r in tab.itertuples()
    )
    aplic = "; ".join(f"{a} usa {int(v)}" for a, v in sorted(usado.items()) if a in ANOS and a != v)
    ids = _usam("per_capita")
    N_VARS[0] += 1
    return (
        f'<article class="ind var" data-eixo="1 6" data-busca="comunidade discentes servidores terceirizados inep pessoas per capita {e(" ".join(ids).lower())}">'
        f'<header><span class="id num">comunidade</span><span class="origem">pessoas</span><span class="chip pub">Denominador</span></header>'
        f'<h3>Comunidade acadêmica da UFPB</h3>'
        f'<p class="desc">Contagem da UFPB por ano (<code>ref/comunidade_ufpb.csv</code>): discentes + docentes + técnicos-administrativos + terceirizados. '
        f'Ano sem contagem usa o último disponível{": " + e(aplic) if aplic else ""}. A última coluna mostra, para comparação, a comunidade do Censo INEP '
        f'(só graduação, docentes em exercício e técnicos), que fica de reserva.</p>'
        f'<div class="tabela-var"><table><thead><tr><th>Ano</th><th class="r">Discentes</th><th class="r">Docentes</th><th class="r">Técnicos</th>'
        f'<th class="r">Terceirizados</th><th class="r">Comunidade</th><th class="r">INEP</th></tr></thead><tbody>{linhas}</tbody></table></div>'
        f'<p class="nota-ipca">Comunidade usada em: {e(", ".join(ids))}. Servidores (docentes + técnicos, sem terceirizados) usados em: '
        f'{e(", ".join(_usam("pct_servidores")))}.</p></article>'
    )


def _card_area() -> str:
    linhas = "".join(
        f'<tr><th scope="row">Campus {e(r.campus)} · {e(r.unidade)}</th><td class="r num">{num(r.area_m2, "m²")}</td></tr>'
        for r in area.itertuples()
    )
    por_campus = area.groupby("campus")["area_m2"].sum()
    linhas += "".join(f'<tr class="sub"><th scope="row">Campus {c}</th><td class="r num">{num(v, "m²")}</td></tr>'
                      for c, v in por_campus.items())
    linhas += f'<tr class="total"><th scope="row">UFPB</th><td class="r num">{num(area["area_m2"].sum(), "m²")}</td></tr>'
    ids = _usam("valor_por_m2")
    N_VARS[0] += 1
    return (
        f'<article class="ind var" data-eixo="1 2 5" data-busca="area construida m2 campus {e(" ".join(ids).lower())}">'
        f'<header><span class="id num">area_m2</span><span class="origem">m²</span><span class="chip pub">Denominador</span></header>'
        f'<h3>Área construída</h3>'
        f'<p class="desc">Informada ao painel pela UFPB (ref/area_construida.csv), uma fotografia aplicada a todos os anos. '
        f'Consumo por campus divide pela área do campus; UFPB inteira, pela área total.</p>'
        f'<div class="tabela-var"><table><thead><tr><th>Unidade</th><th class="r">Área</th></tr></thead><tbody>{linhas}</tbody></table></div>'
        f'<p class="nota-ipca">Usada em: {e(", ".join(ids))}.</p></article>'
    )


def _card_ipca() -> str:
    t = ipca[ipca["ano"].isin(ANOS)].pivot_table(index="mes", columns="ano", values="indice")
    v = ipca[ipca["ano"].isin(ANOS)].pivot_table(index="mes", columns="ano", values="variacao_pct")
    meses_nome = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]

    def cel(a, m):
        if a not in t.columns or m not in t.index or math.isnan(t.loc[m, a]):
            return '<td class="r">—</td>'
        ind_ = f"{t.loc[m, a]:.6f}".replace(".", ",")
        var = f"{v.loc[m, a]:+.2f}%".replace(".", ",")
        return f'<td class="r"><span class="num">{ind_}</span><small class="corr">{var}</small></td>'

    linhas = "".join(f'<tr><th scope="row">{meses_nome[m - 1]}</th>{"".join(cel(a, m) for a in ANOS)}</tr>' for m in range(1, 13))
    ref = ind["ref_ipca"].dropna().max()
    ids = sorted(r.id for r in cat[cat["automacao"] == "automatico"].itertuples() if "valor_real" in r.calculo or "valor_por_m2" in r.calculo)
    ids = [i for i in ids if cat.set_index("id").loc[i, "unidade"].startswith("R$")]
    N_VARS[0] += 1
    return (
        f'<article class="ind var" data-eixo="1 2 3 5 6" data-busca="ipca inflacao indice correcao deflator">'
        f'<header><span class="id num">ipca</span><span class="origem">número-índice</span><span class="chip pub">Correção</span></header>'
        f'<h3>IPCA (IBGE, série 433 do Banco Central)</h3>'
        f'<p class="desc">Cada valor mensal em R$ é multiplicado por índice de {e(ref_ipca_txt())} ÷ índice do mês do pagamento. '
        f'Índice encadeado a partir da variação mensal (base = 1 no início da série).</p>'
        f'<div class="tabela-var"><table><thead><tr><th>Mês</th>{"".join(f"<th class=r>{a}</th>" for a in ANOS)}</tr></thead>'
        f'<tbody>{linhas}</tbody></table></div>'
        f'<p class="nota-ipca">Referência: {e(str(ref))}. Usado nos indicadores em R$: {e(", ".join(ids))}.</p></article>'
    )


def aba_variaveis() -> str:
    uso = _uso_por_metrica()
    ordem = ["consumo_kwh", "consumo_m3", "consumo_litros", "residuos_kg", "co2e_kg", "pago", "pago_acao", "empenhado_itens",
             "evg_certificados", "evg_pessoas_sust", "emissoes_kgco2e", "empenhado_material_consumo"]
    nums = "".join(_card_metrica(m, uso[m]) for m in ordem if m in uso)
    dens = _card_comunidade() + _card_area() + _card_ipca()
    return (
        f'<section class="eixo" data-eixo=""><h2><span class="n">Numeradores</span> o que é somado '
        f'<small>por recorte e ano, com os indicadores que usam cada recorte</small></h2><div class="grade larga">{nums}</div></section>'
        f'<section class="eixo" data-eixo=""><h2><span class="n">Denominadores e correção</span> por pessoa, por m² e IPCA'
        f'<small>tabelas de referência usadas nas divisões</small></h2><div class="grade larga">{dens}</div></section>'
    )


TEMPLATE = Path(__file__).with_name("indicadores_template.html").read_text(encoding="utf-8")
pagina = (TEMPLATE
          .replace("{{N_AUTO}}", str(len(auto))).replace("{{N_PEND}}", str(len(pend)))
          .replace("{{N_PLANO}}", str(len(plano))).replace("{{N_AUTO_PLANO}}", str(n_auto_plano))
          .replace("{{N_AUTO_AMPL}}", str(len(auto) - n_auto_plano))
          .replace("{{N_PUB}}", str(int(((pend["automacao"] == "integracao") & (pend["tipo_fonte"] == "publica")).sum())))
          .replace("{{N_FORN}}", str(int((pend["tipo_fonte"] == "fornecedor").sum())))
          .replace("{{N_INT}}", str(int((pend["tipo_fonte"] == "interna").sum())))
          .replace("{{N_INF}}", str(int((pend["automacao"] == "informado").sum())))
          .replace("{{DATA}}", date.today().strftime("%d/%m/%Y"))
          .replace("{{EIXOS}}", botoes_eixo)
          .replace("{{VARS}}", aba_variaveis()).replace("{{N_VARS}}", str(N_VARS[0]))
          .replace("{{AUTO}}", aba(auto, True)).replace("{{PEND}}", aba(pend, False)))
assert "{{" not in pagina
OUT.write_text(pagina, encoding="utf-8")
print(OUT, len(auto), len(pend))
