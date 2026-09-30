"""Gera a pagina da proposta de automacao das metas do PLS a partir de
ref/indicadores_pls.csv (mesma fonte do ETL, para os numeros baterem)."""

import html
import json
from pathlib import Path

import pandas as pd

ETL = Path(r"C:\Users\diogo\repositorios\codeinfo\sustentabilidade\pls_ufpb-etl")
OUT = Path(__file__).with_name("automacao_pls_ufpb.html")

cat = pd.read_csv(ETL / "ref" / "indicadores_pls.csv", sep=";", dtype=str, keep_default_na=False)
eixos = pd.read_csv(ETL / "ref" / "eixos_pls.csv", sep=";", dtype=str)
plano = cat[cat["id"].str.startswith("E")]
ampl = cat[cat["id"].str.startswith("A")]

n = len(plano)
auto = int((plano["automacao"] == "automatico").sum())
integ = plano[plano["automacao"] == "integracao"]
pub = int((integ["tipo_fonte"] == "publica").sum())
forn = int((integ["tipo_fonte"] == "fornecedor").sum())
inter = int((integ["tipo_fonte"] == "interna").sum())
inf = int((plano["automacao"] == "informado").sum())
autom_total = auto + pub + forn + inter
assert auto + pub + forn + inter + inf == n
pct = round(100 * autom_total / n)

e = html.escape


def classe(r):
    if r["automacao"] == "automatico":
        return "auto", "Automático hoje"
    if r["automacao"] == "informado":
        return "inf", "Informado pela comissão"
    return {"publica": ("pub", "Integrar: dado público"), "fornecedor": ("forn", "Integrar: fornecedor"),
            "interna": ("int", "Integrar: sistema da UFPB")}[r["tipo_fonte"]]


linhas = []
for ex in eixos.itertuples():
    sub = plano[plano["eixo_pls"] == ex.eixo_pls]
    linhas.append(f'<tr class="eixo-linha" data-eixo="{ex.eixo_pls}"><th colspan="4" scope="colgroup">Eixo {ex.eixo_pls} · {e(ex.eixo)} <span>{len(sub)} indicadores</span></th></tr>')
    for _, r in sub.iterrows():
        cls, rot = classe(r)
        conf = f'<p class="confirmar">A confirmar: {e(r["confirmar"])}</p>' if r["confirmar"] else ""
        linhas.append(
            f'<tr data-eixo="{r["eixo_pls"]}" data-nivel="{cls}">'
            f'<td class="ind"><span class="id">{e(r["id"])}</span><strong>{e(r["indicador"])}</strong>'
            f'<span class="obj">Tabela {e(r["tabela_pls"])} · {e(r["objetivo"])}</span></td>'
            f'<td class="meta">{e(r["meta"])}</td>'
            f'<td><span class="chip {cls}">{rot}</span></td>'
            f'<td class="rota">{e(r["rota_automacao"])}{conf}<span class="resp">Responsável no PLS: {e(r["responsavel"])}</span></td></tr>'
        )

ampl_html = []
for _, r in ampl.iterrows():
    cls, rot = classe(r)
    ampl_html.append(
        f'<li><div class="a-topo"><strong>{e(r["indicador"])}</strong><span class="chip {cls}">{rot}</span></div>'
        f'<p>{e(r["meta"])}. {e(r["rota_automacao"])}</p></li>'
    )

barra = [("auto", auto, "Automático hoje"), ("pub", pub, "Dado público a integrar"), ("forn", forn, "Dado do fornecedor"),
         ("int", inter, "Sistema interno da UFPB"), ("inf", inf, "Informado pela comissão")]
barra_html = "".join(f'<span class="seg {c}" style="flex:{v}" title="{t}: {v}">{v}</span>' for c, v, t in barra)
legenda_html = "".join(f'<li><span class="sw {c}"></span>{t} <b>{v}</b></li>' for c, v, t in barra)

def tabela_faturas() -> str:
    arq = ETL / "data" / "processed" / "pls_faturas.parquet"
    if not arq.exists():
        return ""
    f = pd.read_parquet(arq)
    procs = f.drop_duplicates("processo")
    ok = f[f["status"] == "ok"].copy()
    ok["ano"] = ok["periodo"].str[:4]
    meses = ok.groupby("ano")["periodo"].nunique()
    anos = [a for a in sorted(ok["ano"].dropna().unique()) if a in meses and meses[a] == 12]
    br = lambda v: f"{v:,.0f}".replace(",", ".")  # noqa: E731
    br1 = lambda v: f"{v:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")  # noqa: E731
    area = pd.read_csv(ETL / "ref" / "area_construida.csv", sep=";", dtype={"area_m2": float})
    area_c = area.groupby("campus")["area_m2"].sum()
    ult = anos[-1] if anos else None
    linhas = []
    for campus in ("I", "II", "III", "IV"):
        c = ok[ok["campus"] == campus]
        tds = []
        for a in anos:
            tds.append(f'<td class="r">{br(c[(c["tipo"] == "energia") & (c["ano"] == a)]["kwh"].sum())}</td>')
        for a in anos:
            tds.append(f'<td class="r">{br(c[(c["tipo"] == "agua") & (c["ano"] == a)]["m3"].sum())}</td>')
        kwh_m2 = c[(c["tipo"] == "energia") & (c["ano"] == ult)]["kwh"].sum() / area_c[campus] if ult else 0
        tds.append(f'<td class="r">{br(area_c[campus])}</td><td class="r">{br1(kwh_m2)}</td>')
        linhas.append(f"<tr><td>Campus {campus}</td>{''.join(tds)}</tr>")
    tot = []
    for a in anos:
        tot.append(f'<td class="r"><b>{br(ok[(ok["tipo"] == "energia") & (ok["ano"] == a)]["kwh"].sum())}</b></td>')
    for a in anos:
        tot.append(f'<td class="r"><b>{br(ok[(ok["tipo"] == "agua") & (ok["ano"] == a)]["m3"].sum())}</b></td>')
    kwh_m2_t = ok[(ok["tipo"] == "energia") & (ok["ano"] == ult)]["kwh"].sum() / area["area_m2"].sum() if ult else 0
    tot.append(f'<td class="r"><b>{br(area["area_m2"].sum())}</b></td><td class="r"><b>{br1(kwh_m2_t)}</b></td>')
    linhas.append(f"<tr><td><b>UFPB</b></td>{''.join(tot)}</tr>")
    cab = "".join(f'<th class="r">kWh {a}</th>' for a in anos) + "".join(f'<th class="r">m³ {a}</th>' for a in anos) + f'<th class="r">Área (m²)</th><th class="r">kWh/m² {ult}</th>'
    n_ok, n = int((procs["status"] == "ok").sum()), len(procs)
    return (f'<div class="tabela-box"><table><thead><tr><th>Campus</th>{cab}</tr></thead><tbody>{"".join(linhas)}</tbody></table></div>'
            f'<p style="margin-top:.8rem">{n_ok} de {n} processos de pagamento de 2024 a 2026 lidos automaticamente. '
            f'Consumo pelo mês de referência da fatura; energia pelo kWh medido de cada unidade consumidora. '
            f'Conferência: dezembro/2024 bate exatamente com a Tabela 11 do PLS (12.833, 4.589 e 1.107 m³ nos Campi I, II e IV).</p>'
            + tabela_frota_residuos(ok, anos))


def tabela_frota_residuos(ok, anos) -> str:
    br = lambda v: f"{v:,.0f}".replace(",", ".")  # noqa: E731
    c = ok[ok["tipo"] == "combustivel"]
    r = ok[ok["tipo"] == "residuos"]
    linhas = []
    for campus in ("I", "II", "III", "IV", None):
        cc = c if campus is None else c[c["campus"] == campus]
        rr = r if campus is None else r[r["campus"] == campus]
        nome = "<b>UFPB</b>" if campus is None else f"Campus {campus}"
        tds = [f'<td class="r">{br(cc[(cc["ano"] == a) & (cc["combustivel"] == comb)]["litros"].sum())}</td>'
               for a in anos for comb in ("diesel", "gasolina")]
        tds += [f'<td class="r">{br(rr[rr["ano"] == a]["kg"].sum()) if len(rr) else "—"}</td>' for a in anos]
        linhas.append(f"<tr><td>{nome}</td>{''.join(tds)}</tr>")
    cab = "".join(f'<th class="r">Diesel {a} (L)</th><th class="r">Gasolina {a} (L)</th>' for a in anos)
    cab += "".join(f'<th class="r">Resíduos {a} (kg)</th>' for a in anos)
    return (f'<div class="tabela-box" style="margin-top:1rem"><table><thead><tr><th>Campus</th>{cab}</tr></thead>'
            f'<tbody>{"".join(linhas)}</tbody></table></div>'
            '<p style="margin-top:.8rem">Combustível: duas gerenciadoras (GOLDI até mai/2024, PRIME depois) e quatro modelos de relatório lidos; o extrato da GOLDI '
            '(até mai/2024) confere ao centavo com o total das faturas. <b>Lacuna:</b> jun a ago/2024 a gerenciadora só '
            'anexou tickets em R$, sem litros; o relatório precisa ser pedido à SULT. Etanol: 305 L em 2024, zero em 2025. Campus pela subunidade do veículo; a queda do diesel do Campus IV em 2025 deve ser confirmada com a SULT. '
            'Resíduos de saúde (grupos A, B e E): Campus IV não tem coleta contratada.</p>')


TEMPLATE = Path(__file__).with_name("proposta_template.html").read_text(encoding="utf-8")
pagina = (TEMPLATE
          .replace("{{N}}", str(n)).replace("{{AUTO}}", str(auto)).replace("{{PUB}}", str(pub))
          .replace("{{FORN}}", str(forn)).replace("{{INT}}", str(inter)).replace("{{INF}}", str(inf))
          .replace("{{AUTOM_TOTAL}}", str(autom_total)).replace("{{PCT}}", str(pct))
          .replace("{{N_AMPL}}", str(len(ampl))).replace("{{AMPL_AUTO}}", str(int((ampl["automacao"] == "automatico").sum())))
          .replace("{{BARRA}}", barra_html).replace("{{LEGENDA}}", legenda_html)
          .replace("{{FATURAS}}", tabela_faturas())
          .replace("{{LINHAS}}", "\n".join(linhas)).replace("{{AMPLIACOES}}", "\n".join(ampl_html)))
assert "{{" not in pagina
OUT.write_text(pagina, encoding="utf-8")
print(OUT, n, auto, pub, forn, inter, inf, pct)
