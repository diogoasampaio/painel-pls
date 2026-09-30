"""Exemplo rastreado de cada indicador do nucleo: um registro real seguido da
fonte ate o valor do indicador, para quem valida a metodologia refazer a conta
a mao (numero do processo, documento, empenho, contratacao...).

LGPD: pagamento a pessoa fisica aparece sem nome e sem observacao; MEI (cujo
nome empresarial costuma ser o nome da pessoa) nao e escolhido como exemplo;
capacitacao (N13) so em numeros agregados."""

from __future__ import annotations

import re
from functools import lru_cache

import pandas as pd

from common.storage import load_processed, read_json, raw_path
from relatorios.blocos import Doc, num

TIPO_FATURA = {"N01": ("energia", "kwh", "kWh"), "N02": ("agua", "m3", "m³"), "N04": ("residuos", "kg", "kg"),
               "N07": ("combustivel", "litros", "L")}
PNCP_EDITAL = "https://pncp.gov.br/app/editais/{cnpj}/{ano}/{seq}"


@lru_cache
def _t(nome: str) -> pd.DataFrame:
    return load_processed(nome)


def _rs(v) -> str:
    return num(v, "R$")


def _cache_sipac(processo: str) -> dict:
    n, ano = processo.split("/")[0], processo.split("/")[1][:4]
    arq = raw_path("sipac", ano, f"{processo.replace('/', '_')}.json")
    return read_json(arq) if arq.exists() else {}


def _mes_fechado(ano: int) -> str:
    return f"{ano}-10"  # outubro: mes com todas as fontes publicadas e longe das viradas de contrato


def fatura(doc: Doc, codigo: str, ano: int):
    tipo, campo, un = TIPO_FATURA[codigo]
    f = _t("pls_faturas")
    f = f[(f["tipo"] == tipo) & (f["status"] == "ok") & (f["periodo"] == _mes_fechado(ano))]
    if f.empty:
        doc.p("Sem processo lido no mês de exemplo.")
        return
    # o processo com mais consumo no mes (Campus I, em geral)
    proc = f.groupby("processo")[campo].sum().idxmax()
    p = f[f["processo"] == proc]
    c = _cache_sipac(proc)
    doc_lido = next((x["especie"] for x in c.get("documentos", []) if x["ordem"] == c.get("documento")), "")
    total_mes = f[campo].sum()
    passos = [
        f"**Portal da Transparência:** pagamento(s) de {p['data_pagamento'].iloc[0]} na UG {p['ug'].iloc[0]}, "
        f"no total de {_rs(p['pago_portal_processo'].iloc[0])}, com o processo **23074.{proc}** no campo Processo "
        f"(ou na observação)" + (f", fatura {p['fatura_portal'].iloc[0]}" if isinstance(p['fatura_portal'].iloc[0], str) else "") + ".",
        f"**SIPAC:** o processo 23074.{proc} tem {len(c.get('documentos', []))} documentos; o painel leu o de ordem "
        f"{c.get('documento', '—')} ({doc_lido.lower() or 'documento'}). Assunto: “{(c.get('assunto') or '').strip()[:180]}”.",
    ]
    if tipo == "combustivel":
        por = p.groupby("combustivel_texto")["litros"].agg(["count", "sum"]).sort_values("sum", ascending=False)
        passos.append("**Leitura do relatório:** " + "; ".join(
            f"{k}: {int(r['count'])} abastecimento(s), {num(r['sum'])} L" for k, r in por.iterrows()) + ".")
    else:
        linha = {"energia": "unidade(s) consumidora(s)", "agua": "ligação(ões)", "residuos": "campus(i)"}[tipo]
        passos.append(f"**Leitura do documento:** {len(p)} {linha}, "
                      f"somando {num(p[campo].sum())} {un} no mês de referência {_mes_fechado(ano)}.")
    passos.append(f"**Soma do mês:** com os demais processos do mesmo mês ({f['processo'].nunique()} no total), "
                  f"o painel chega a {num(total_mes)} {un} em {_mes_fechado(ano)}, que entram na soma do ano da tabela "
                  f"de cálculo.")
    doc.passos(passos)
    if tipo != "combustivel":
        cols = {"energia": ["uc", "kwh_faturado", "kwh_medido", "kwh", "valor_bruto"],
                "agua": ["uc", "m3_faturado", "m3_medido", "m3", "valor_bruto"],
                "residuos": ["uc", "kg", "valor"]}[tipo]
        rot = {"uc": "Unidade", "kwh_faturado": "kWh faturado", "kwh_medido": "kWh medido", "kwh": "kWh usado",
               "m3_faturado": "m³ faturado", "m3_medido": "m³ medido", "m3": "m³ usado", "kg": "kg",
               "valor_bruto": "Valor (R$)", "valor": "Valor (R$)"}
        linhas = [[str(x[cols[0]])] + [num(x[k]) for k in cols[1:]] for _, x in p.sort_values(campo, ascending=False).head(8).iterrows()]
        doc.tabela(f"{codigo}: linhas lidas no processo 23074.{proc} ({_mes_fechado(ano)})", [rot[k] for k in cols],
                   linhas, num=set(range(1, len(cols))), larg=[1.6] + [1] * (len(cols) - 1),
                   fonte=f"SIPAC, processo 23074.{proc}" + (" (até 8 linhas, das maiores)" if len(p) > 8 else ""))


def pagamento(doc: Doc, codigo: str, ano: int):
    d = _t("pls_despesas")
    d = d[(d["fase"] == "pagamento") & (d["ano"] == ano)]
    if codigo == "N05":
        sel = d[d["subtema"].isin(["Limpeza e conservação"])]
        alvo = "limpeza e conservação (uma das quatro parcelas do custo de funcionamento)"
    elif codigo == "N06":
        sel, alvo = d[d["tema_codigo"] == "manutencao_predial"], "manutenção predial"
    else:
        sel, alvo = d[d["acao"] == "4572"], "capacitação (ação 4572)"
    sel = sel.assign(pg=sel["valor_pago"].fillna(0) + sel["valor_rp_pago"].fillna(0))
    sel = sel[(sel["pg"] > 0) & (sel["mes"] == 10)]
    # exemplo mais claro: ordem bancaria (OB) a empresa; retencao de tributo (DF) e banco ficam por ultimo
    pj = sel[(sel["favorecido_tipo"] == "PJ") & sel["documento"].str.contains("OB")
             & ~sel["favorecido_nome"].fillna("").str.upper().str.contains("BANCO")]
    x = (pj if not pj.empty else sel).sort_values("pg", ascending=False)
    if x.empty:
        doc.p("Sem pagamento no mês de exemplo.")
        return
    x = x.iloc[0]
    ipca = _t("pls_ipca").set_index("periodo")["indice"]
    ref = ipca.index.max()
    fator = ipca[ref] / ipca[x["periodo"]] if x["periodo"] in ipca.index else float("nan")
    fav = x["favorecido_nome"] if x["favorecido_tipo"] == "PJ" else "pessoa física (nome omitido)"
    area = _t("pls_indicadores")
    area = area[(area["metrica"] == "pago") & (area["ano"] == ano)].drop_duplicates("area_m2")["area_m2"].max()
    doc.passos([
        f"**Portal da Transparência:** pagamento {x['documento']} de {pd.Timestamp(x['data']):%d/%m/%Y}, UG {x['ug']}, "
        f"empenho {x['empenho']}, natureza {x['natureza']}, favorecido {fav}: pago {_rs(x['valor_pago'])} + restos a "
        f"pagar pagos {_rs(x['valor_rp_pago'])} = **{_rs(x['pg'])}**."
        + (f" Observação: “{str(x['observacao'])[:160]}”." if x["favorecido_tipo"] == "PJ" and x["observacao"] else ""),
        (f"**Classificação:** o empenho {x['empenho']} é da ação orçamentária 4572 (capacitação de servidores), "
         f"lida no arquivo do dia em que o empenho foi emitido. Pela ação, entra com qualquer natureza."
         if codigo == "N14" else
         f"**Classificação:** a natureza {x['natureza']} está em `ref/mapeamento_natureza_pls.csv` como "
         f"“{x['subtema']}”, parcela de {alvo}."),
        f"**Correção pelo IPCA:** índice de {ref} ÷ índice de {x['periodo']} = {str(round(fator, 4)).replace('.', ',')}; "
        f"{_rs(x['pg'])} × {str(round(fator, 4)).replace('.', ',')} = {_rs(x['pg'] * fator)} em R$ de {ref}.",
        f"**Soma:** o pagamento entra no mês {x['periodo']} com os demais da mesma parcela; a soma dos 12 meses "
        f"corrigidos é o numerador da tabela de cálculo."
        + (f" O denominador é a área construída de `ref/area_construida.csv` ({num(area)} m²)."
           if codigo in ("N05", "N06") and area == area else ""),
    ])


def gee(doc: Doc, ano: int):
    mes = _mes_fechado(ano)
    i = _t("pls_indicadores")
    i = i[i["periodo"] == mes]
    sin = _t("pls_fator_sin").set_index("periodo")["fator_t_mwh"]
    kwh = i[i["metrica"] == "consumo_kwh"]["valor_nominal"].sum()
    lit = i[i["metrica"] == "consumo_litros"].groupby("subtema")["valor_nominal"].sum()
    em = i[i["metrica"] == "emissoes_kgco2e"].groupby("subtema")["valor_nominal"].sum()
    f = sin.get(mes)
    from common import pls_map
    from indicadores.build_indicadores import _fator
    fat = pls_map._read_ref("fatores_gee")
    fat["valor"] = pd.to_numeric(fat["valor"])
    bio, _ = _fator(fat, "biodiesel_no_diesel", mes)
    eta, _ = _fator(fat, "etanol_na_gasolina", mes)
    diesel = lit[lit.index.str.contains("diesel")].sum()
    gas = lit[lit.index.str.contains("gasolina")].sum()
    linhas = [
        ["Escopo 2 · energia", f"{num(kwh)} kWh", f"{str(f).replace('.', ',')} kg CO₂/kWh (MCTI, {mes})",
         num(em.get("Escopo 2 · energia elétrica", 0) / 1000)],
        ["Escopo 1 · diesel", f"{num(diesel)} L", f"2,677 kg CO₂/L × (1 − {str(bio).replace('.', ',')} de biodiesel)",
         num(em.get("Escopo 1 · frota (diesel)", 0) / 1000)],
        ["Escopo 1 · gasolina", f"{num(gas)} L", f"2,278 kg CO₂/L × (1 − {str(eta).replace('.', ',')} de etanol anidro)",
         num(em.get("Escopo 1 · frota (gasolina)", 0) / 1000)],
        ["Escopo 3 · viagens aéreas", "trechos do mês", "kg CO₂e por passageiro-km, por faixa de distância",
         num(em.get("Escopo 3 · viagens aéreas", 0) / 1000)],
        ["**Total do mês**", "", "", f"**{num(em.sum() / 1000)}**"],
    ]
    doc.p(f"Conta do mês de {mes}, com os consumos que o painel leu nas faturas, nos relatórios da frota e nas viagens:")
    doc.tabela(f"N03: emissões de {mes}", ["Parcela", "Consumo", "Fator", "t CO₂e"], linhas, num={1, 3},
               larg=[1.6, 1.4, 3, 1])


def material(doc: Doc, ano: int):
    it = _t("pls_itens_empenho")
    it = it[(it["ano"] == ano) & it["regras_texto"].map(lambda r: "item_sustentavel" in list(r))]
    if it.empty:
        doc.p("Sem item com atributo sustentável no ano.")
        return
    x = it.sort_values("valor", ascending=False).iloc[0]
    doc.passos([
        f"**Portal da Transparência (itens de empenho):** empenho {x['empenho']}, de {pd.Timestamp(x['data']):%d/%m/%Y}, "
        f"UG {x['ug']}, natureza {x['natureza']}: item “{str(x['descricao'])[:200]}”, valor {_rs(x['valor'])}.",
        "**Regra de texto:** a descrição, sem acento e em minúsculas, casa a regra `item_sustentavel` de "
        "`ref/regras_texto_pls.csv`; o item entra no numerador.",
        f"**Denominador:** todos os itens de material de consumo (3.3.90.30) empenhados em {ano}: "
        f"{len(_t('pls_itens_empenho').query('ano == @ano and natureza.str.startswith(\"339030\")', engine='python'))} "
        f"itens; {len(it)} deles têm atributo sustentável.",
    ])


def edital(doc: Doc, ano: int):
    c = _t("pls_compras")
    c = c[(c["ano"] == ano) & (c["nivel_sustentabilidade"] == "especifico")]
    if c.empty:
        doc.p("Sem contratação com critério específico no ano.")
        return
    x = c.sort_values("valor", ascending=False).iloc[0]
    cnpj, _, resto = x["controle"].split("-", 2)
    seq, ano_c = resto.split("/")
    link = PNCP_EDITAL.format(cnpj=cnpj, ano=ano_c, seq=int(seq))
    trecho = list(x["trechos"])[0] if len(x["trechos"]) else ""
    doc.passos([
        f"**Compras.gov.br:** contratação {x['controle']} ({x['modalidade']}), publicada em {x['data_publicacao']}, "
        f"valor {_rs(x['valor'])}. Objeto: “{str(x['objeto'])[:200]}”.",
        f"**PNCP:** documentos lidos: {', '.join(list(x['documentos_lidos'])) or '—'}. Link: {link}",
        f"**Critérios obrigatórios encontrados (fora do ETP):** {'; '.join(list(x['criterios']))}.",
        f"**Trecho que casou a regra:** “{trecho[:300]}”.",
        "**Resultado:** a contratação conta no numerador e no denominador do N10.",
    ])


def compartilhada(doc: Doc, ano: int):
    s = _t("pls_compras_compartilhadas")
    s = s[s["ano"] == ano]
    if s.empty:
        doc.p("Sem compra compartilhada no ano.")
        return
    x = s.iloc[0]
    doc.passos([
        f"**Tipo:** {x['tipo']}. Referência: {x['referencia']}" + (f", compra {x['compra']}" if x["compra"] else "")
        + f", data {x['data']}.",
        f"**Detalhe lido na fonte:** {str(x['detalhe'])[:260]}.",
        f"**Contagem:** cada compra conta uma vez por tipo; em {ano} foram {len(s)} ("
        + "; ".join(f"{k}: {v}" for k, v in s["tipo"].value_counts().items()) + ").",
    ])


def fornecedor(doc: Doc, ano: int):
    p, f = _t("pls_pagamentos_pj"), _t("pls_fornecedores").set_index("cnpj")
    p = p[(p["ano"] == ano) & (p["subtema"] == "ME/EPP da Paraíba")]
    p = p[p["cnpj"].map(lambda c: c in f.index and f.loc[c, "opcao_mei"] != "S")]
    if p.empty:
        doc.p("Sem pagamento a ME/EPP da Paraíba no ano.")
        return
    cnpj = p.groupby("cnpj")["valor"].sum().idxmax()
    x = f.loc[cnpj]
    tot = p[p["cnpj"] == cnpj]["valor"].sum()
    doc.passos([
        f"**Portal da Transparência:** em {ano} a UFPB pagou {_rs(tot)} ao CNPJ {cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/"
        f"{cnpj[8:12]}-{cnpj[12:]} ({x['razao_social']}) em naturezas de contratação.",
        f"**Receita Federal (cadastro de {x['mes_cadastro']}):** porte {x['porte']} ({x['porte_descricao']}), "
        f"estabelecimento na UF {x['uf']} (município código {x['municipio']} da tabela da Receita), CNAE "
        f"{x['cnae_principal']}, optante do Simples: {({'S': 'sim', 'N': 'não'}).get(x['opcao_simples'], 'sem registro')}.",
        "**Classificação:** porte 01 ou 03 → ME/EPP; UF PB → Paraíba. O valor entra no numerador (ME/EPP da Paraíba) "
        "e no denominador.",
    ])


def capacitacao(doc: Doc, ano: int):
    e = _t("pls_evg")
    e = e[(e["ano"] == ano) & e["concluida"] & e["sustentabilidade"]]
    cursos = e.drop_duplicates(["pessoa", "cod_curso"])["nome_curso"].value_counts().head(5)
    doc.passos([
        f"**Arquivos da ENAP de {ano}:** {len(e)} certificações em cursos de sustentabilidade de alunos que declaram a "
        f"UFPB, de {e['pessoa'].nunique()} pessoas distintas (contadas pelo código anônimo).",
        "**Cursos mais frequentes:** " + "; ".join(f"{k} ({v})" for k, v in cursos.items()) + ".",
        "**Denominador:** docentes em exercício + técnicos do Censo INEP. Por LGPD o exemplo fica agregado: não há "
        "exemplo individual.",
    ])


def acao(doc: Doc):
    a = _t("pls_acoes")
    ver = a[a["verificada_painel"] & (a["evidencia_painel"] != "")]
    sem = a[a["situacao"] == "vencida_sem_informacao"]
    itens = []
    if not ver.empty:
        x = ver.iloc[0]
        ev = re.sub(r"^[a-z0-9_]+(?: \((.+?)\))?:", lambda m: (m.group(1) or "dados do painel") + ":", x["evidencia_painel"])
        itens.append(f"**Ação verificada pelos dados:** {x['id']} “{x['acao']}” ({x['responsavel']}), contínua: o painel "
                     f"verificou ({ev}) → situação “em dia”, conta no numerador.")
    if not sem.empty:
        x = sem.iloc[0]
        itens.append(f"**Ação com prazo vencido:** {x['id']} “{x['acao']}” ({x['responsavel']}), fim previsto "
                     f"{x['fim']}, sem registro no formulário → “prazo vencido sem informação”, conta só no denominador.")
    doc.passos(itens)


def rastrear(doc: Doc, codigo: str, ano: int):
    if codigo in TIPO_FATURA:
        fatura(doc, codigo, ano)
    elif codigo in ("N05", "N06", "N14"):
        pagamento(doc, codigo, ano)
    elif codigo == "N03":
        gee(doc, ano)
    elif codigo == "N09":
        material(doc, ano)
    elif codigo == "N10":
        edital(doc, ano)
    elif codigo == "N11":
        compartilhada(doc, ano)
    elif codigo == "N12":
        fornecedor(doc, ano)
    elif codigo == "N13":
        capacitacao(doc, ano)
    elif codigo == "N15":
        acao(doc)
    else:
        doc.p("Sem dado no painel para rastrear: o valor depende do lançamento do setor responsável.")
