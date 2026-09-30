"""Agregados mensais do painel -> colecao pls_indicadores.

Le os parquet de data/processed/ (nao o Mongo): roda depois dos modulos de
fonte e nao precisa de banco para o dry-run. Formato longo, um documento
por (periodo, tema, subtema, metrica):

  valor_nominal          soma no mes, em R$ correntes (ou unidade fisica)
  valor_real             R$ a precos do ultimo mes com IPCA (ref_ipca)
  valor_real_per_capita  valor_real / comunidade academica do ano (common/comunidade.py:
                         contagem da UFPB em ref/comunidade_ufpb.csv, com o Censo INEP
                         de reserva); ano sem contagem usa o ultimo disponivel
                         (ano_comunidade mostra qual)
  valor_por_m2           valor_real / area construida (ref/area_construida.csv):
                         do campus quando o subtema e "Campus X" (consumo das
                         faturas), da UFPB inteira nos demais. A area e uma
                         fotografia unica, aplicada a todos os anos.

Todas as colunas sao aditivas entre subtemas -- a API pode somar para o
tema inteiro sem recalcular deflator ou denominador.

Metricas:
  liquidado, pago         (R$)   pls_despesas por fase
  pago_acao               (R$)   pago nas acoes orcamentarias do PLS (ref/acoes_pls.csv,
                                 ex.: 4572 capacitacao), todas as naturezas; subtema =
                                 "Acao <codigo> · <elemento de despesa>"
  empenhado_itens         (R$)   pls_itens_empenho que casaram regra de
                                 texto (papel A4, copos, LED, fotovoltaica...)
  quantidade_itens        (copos, resmas, cartuchos) quantidade comprada de copos, papel A4 e
                                 toner: valor empenhado / preco homologado da compra no PNCP
                                 (compras/quantidades.py); unidade por subtema
  empenhado_material_consumo (R$) itens de material de consumo (3.3.90.30) empenhados, com
                                 subtema "Com atributo sustentavel" / "Demais itens"
  consumo_kwh, consumo_m3 (kWh, m³) pls_faturas: consumo medido nas faturas
                                 da Energisa e da CAGEPA (SIPAC), pelo mes de
                                 REFERENCIA da fatura; subtema = campus
  consumo_litros          (L)    pls_faturas: abastecimentos da gerenciadora de
                                 frota, pelo mes do abastecimento; subtema =
                                 "Frota - <combustivel>"
  viagens                 (un)   pls_viagens realizadas, pelo mes de inicio
  evg_matriculas, evg_certificados, evg_horas_certificadas, evg_pessoas_sust
                          (un, h, pessoas) pls_evg: cursos da Escola Virtual de Governo
                                 com a UFPB declarada pelo aluno, pelo mes da matricula;
                                 subtema = "EVG · sustentabilidade" / "EVG · demais temas"
  pct_servidores (coluna) valor_nominal / (docentes + tecnicos, mesma fonte) x 100
  adesao_avn_pct          (%)    UGs que pagaram o operador do AVN no ano / UGs da UFPB (E1-AVN-01),
                                 um valor por ano no ultimo mes com despesas
  emissoes_kgco2e         (kg CO2e) inventario de GEE: frota (escopo 1), energia da rede
                                 (escopo 2) e viagens aereas (escopo 3), fatores em
                                 ref/fatores_gee.csv; subtema = escopo
  trechos_aereos, km_aereo, co2e_kg   pls_trechos com meio aereo
  contratacoes_pncp       (un)   pls_compras: contratacoes publicadas no PNCP, pelo mes de publicacao;
  contratacoes_pncp_valor (R$)   subtema = "<Licitacao|Dispensa|Inexigibilidade|Outras> · <nivel do
                                 criterio de sustentabilidade no edital/TR>"
  editais_marcadores      (un)   pls_compras: "<universo> · com|sem <marcador>" (margem de preferencia
                                 nas licitacoes, cota para mulheres e mao de obra local na mao de obra
                                 exclusiva, agricultura familiar nos alimentos, BIM nas obras)
  compras_compartilhadas  (un)   pls_compras_compartilhadas: subtema = tipo (IRP com participante externo,
                                 adesao de outro orgao a ata da UFPB, participacao/adesao da UFPB em
                                 compra de outro orgao)
  pago_fornecedores       (R$)   pls_pagamentos_pj: pago a PJ nas naturezas de contratacao,
                                 subtema = porte (ME/EPP ou demais) x sede (PB ou outros
                                 estados) pelo cadastro aberto de CNPJ da Receita, mais
                                 "Agricultura familiar", "Sem cadastro na Receita" e
                                 "Instituicao financeira" (fora da razao do N12)
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from common import comunidade
from common.mongo import replace_by
from common.storage import load_processed, save_processed
from common.validation import report_counts

COLLECTION = "pls_indicadores"
CHAVE = ["periodo", "tema_codigo", "subtema", "metrica"]


def _despesas() -> pd.DataFrame:
    df = load_processed("pls_despesas")
    if df.empty:
        return df
    from common import pls_map

    if "natureza" in df:
        # tema pela tabela vigente em ref/: mudar o mapeamento nao exige
        # reprocessar (nem baixar de novo) as despesas
        tem = df["natureza"].notna()
        cls = df.loc[tem, "natureza"].map(pls_map.classificar_natureza)
        df.loc[tem, "tema_codigo"] = cls.map(lambda c: c.tema_codigo)
        df.loc[tem, "subtema"] = cls.map(lambda c: c.subtema)
    # Almoxarifado Virtual Nacional: empenhado como servico (3.3.90.39-84), mas e fornecimento de
    # material de consumo. Reconhecido pelo CNPJ do operador (ref/avn_operadores.csv)
    from compras.avn import operadores

    if "favorecido_codigo" in df:
        avn = df["favorecido_codigo"].isin(operadores()) & (df["tema_codigo"] == pls_map.NAO_CLASSIFICADO)
        df.loc[avn, "tema_codigo"] = "material_consumo"
        df.loc[avn, "subtema"] = "Almoxarifado Virtual Nacional (AVN)"
    acao = df["acao"] if "acao" in df else pd.Series(None, index=df.index, dtype=object)
    natureza = df["natureza"] if "natureza" in df else pd.Series(None, index=df.index, dtype=object)
    if "natureza" in df:
        _separar_selecao(df, acao)
    df = df.assign(metrica=df["fase"].map({"liquidacao": "liquidado", "pagamento": "pago"}), unidade="R$")
    # linhas que so entraram por estar numa acao do PLS (natureza fora do mapeamento)
    # nao mudam liquidado/pago: aparecem so em pago_acao
    so_acao = ~natureza.fillna("").str[:6].map(lambda n: pls_map.elemento_relevante(n or None)).astype(bool)
    partes = [df[~so_acao].groupby([*CHAVE, "unidade"], dropna=False, as_index=False)["valor"].sum()]
    acoes = pls_map.acoes()
    na_acao = df[(df["metrica"] == "pago") & acao.isin(acoes)]
    if not na_acao.empty:
        rotulo = natureza[na_acao.index].fillna("").str[:6].map(lambda n: ELEMENTO.get(n[4:6], f"Elemento {n[4:6]}"))
        na_acao = na_acao.assign(
            metrica="pago_acao", tema_codigo=acao[na_acao.index].map(acoes),
            subtema="Ação " + acao[na_acao.index] + " · " + rotulo,
        )
        partes.append(na_acao.groupby([*CHAVE, "unidade"], dropna=False, as_index=False)["valor"].sum())
    return pd.concat(partes, ignore_index=True)


# elemento de despesa (5o e 6o digitos da natureza) -> rotulo, para os subtemas de pago_acao
ELEMENTO = {
    "14": "Diárias", "18": "Auxílio financeiro a estudantes", "20": "Auxílio financeiro a pesquisadores",
    "30": "Material de consumo", "33": "Passagens e locomoção", "36": "Serviços de pessoa física",
    "39": "Serviços de pessoa jurídica", "52": "Equipamentos e material permanente",
    "92": "Despesas de exercícios anteriores",
}
# natureza que mistura concurso/selecao com treinamento (Servicos de selecao e treinamento)
NATUREZA_SELECAO = "33903948"
_CONCURSO = (r"CONCURSO|PROCESSO SELETIVO|SELE[CÇ][AÃ]O P[UÚ]BLICA|VESTIBULAR|"
             r"IBFC|CEBRASPE|CESPE|FUNDA[CÇ][AÃ]O GET[UÚ]LIO VARGAS|IDECAN|FUNDATEC|VUNESP|CESGRANRIO|AOCP|COMPERVE|QUADRIX|CONSULPLAN")


def _separar_selecao(df: pd.DataFrame, acao: pd.Series) -> None:
    """33903948 em tres subtemas: concurso/selecao (recrutamento, nao capacitacao),
    treinamento na acao 4572 e treinamento pago por outras acoes."""
    nat = df["natureza"] == NATUREZA_SELECAO
    if not nat.any():
        return
    texto = (df["observacao"].fillna("") + " " + df["favorecido_nome"].fillna("")).str.upper() \
        if "observacao" in df else pd.Series("", index=df.index)
    concurso = nat & texto.str.contains(_CONCURSO, regex=True)
    df.loc[nat, "subtema"] = "Treinamento (outras ações)"
    # so a natureza 33903948 paga pela 4572: o N14 soma todas as naturezas da acao
    df.loc[nat & acao.isin(["4572"]), "subtema"] = "Serviços de treinamento (ação 4572)"
    df.loc[concurso, "subtema"] = "Concurso e seleção"


def _itens() -> pd.DataFrame:
    df = load_processed("pls_itens_empenho")
    if df.empty or "regras_texto" not in df:
        return pd.DataFrame()
    from common import pls_map

    regras = pls_map._read_ref("regras_texto_pls").set_index("regra")
    ex = df.explode("regras_texto").dropna(subset=["regras_texto"])
    if ex.empty:
        return pd.DataFrame()
    ex["tema_codigo"] = ex["regras_texto"].map(regras["tema_codigo"])
    ex["subtema"] = ex["regras_texto"].map(regras["subtema"])
    valor = ex.groupby(["periodo", "tema_codigo", "subtema"], as_index=False)["valor"].sum()
    valor = valor.assign(metrica="empenhado_itens", unidade="R$")
    # quantidade comprada (copos, resmas, cartuchos): valor / preco da compra, em compras/quantidades.py
    q = load_processed("pls_itens_quantidade")
    qtd = pd.DataFrame()
    if not q.empty:
        q = q.dropna(subset=["quantidade"])
        qtd = (q.groupby(["periodo", "subtema", "unidade_base"], as_index=False)["quantidade"].sum()
               .rename(columns={"quantidade": "valor", "unidade_base": "unidade"})
               .assign(metrica="quantidade_itens", tema_codigo="material_consumo"))
    # denominador do % de material sustentavel: todo o material de consumo (3.3.90.30) empenhado
    mc = df[df["natureza"].fillna("").str.startswith("339030")]
    sust = mc["regras_texto"].map(lambda r: "item_sustentavel" in list(r) if r is not None else False)
    mat = (mc.assign(subtema=np.where(sust, "Com atributo sustentável", "Demais itens"))
           .groupby(["periodo", "subtema"], as_index=False)["valor"].sum()
           .assign(metrica="empenhado_material_consumo", tema_codigo="compras_sustentaveis", unidade="R$"))
    return pd.concat([valor, qtd, mat], ignore_index=True)


def _faturas() -> pd.DataFrame:
    df = load_processed("pls_faturas")
    if df.empty or "status" not in df:
        return pd.DataFrame()
    df = df[(df["status"] == "ok") & df["periodo"].notna()]
    df = df.assign(subtema="Campus " + df["campus"].fillna("?"))
    partes = []
    for tipo, col, metrica, tema, unidade in (
        ("energia", "kwh", "consumo_kwh", "energia", "kWh"),
        ("agua", "m3", "consumo_m3", "agua_esgoto", "m³"),
        ("residuos", "kg", "residuos_kg", "residuos", "kg"),
    ):
        sub = df[df["tipo"] == tipo]
        if sub.empty or col not in sub:
            continue
        g = sub.groupby(["periodo", "subtema"], as_index=False)[col].sum().rename(columns={col: "valor"})
        partes.append(g.assign(metrica=metrica, tema_codigo=tema, unidade=unidade))
    comb = df[df["tipo"] == "combustivel"] if "litros" in df else pd.DataFrame()
    if not comb.empty:
        g = (comb.assign(subtema=_subtema_combustivel(comb))
             .groupby(["periodo", "subtema"], as_index=False)["litros"].sum().rename(columns={"litros": "valor"}))
        partes.append(g.assign(metrica="consumo_litros", tema_codigo="deslocamento", unidade="L"))
    return pd.concat(partes, ignore_index=True) if partes else pd.DataFrame()


def _subtema_combustivel(comb: pd.DataFrame) -> pd.Series:
    """'Frota - <combustivel>'; o diesel separado em S10 e comum (a matriz SEGES conta o
    S10 como menos poluente). Diesel sem especificacao conta como comum (conservador)."""
    sub = "Frota - " + comb["combustivel"].fillna("outro")
    texto = comb["combustivel_texto"].fillna("").str.upper().str.replace(" ", "") if "combustivel_texto" in comb         else pd.Series("", index=comb.index)
    diesel = comb["combustivel"] == "diesel"
    sub[diesel] = np.where(texto[diesel].str.contains("S10"), "Frota - diesel S10", "Frota - diesel comum")
    return sub


def _viagens() -> pd.DataFrame:
    partes = []
    # uma viagem que cruza a virada do ano pode constar nos zips de dois anos
    v = load_processed("pls_viagens")
    if not v.empty:
        v = v.sort_values("ano").drop_duplicates("id_viagem", keep="last")
        realizadas = v[v["situacao"].str.lower().str.startswith("realizada", na=False)]
        partes.append(
            realizadas.groupby("periodo", as_index=False).size().rename(columns={"size": "valor"})
            .assign(metrica="viagens", unidade="un")
        )
    t = load_processed("pls_trechos")
    if not t.empty:
        t = t.sort_values("ano").drop_duplicates(["id_viagem", "sequencia"], keep="last")
        a = t[t["meio_transporte"] == "aereo"]
        g = a.groupby("periodo").agg(trechos_aereos=("id_viagem", "size"), km_aereo=("distancia_km", "sum"), co2e_kg=("kg_co2e", "sum"))
        unid = {"trechos_aereos": "un", "km_aereo": "km", "co2e_kg": "kg CO2e"}
        partes.append(
            g.reset_index().melt(id_vars="periodo", var_name="metrica", value_name="valor")
            .assign(unidade=lambda d: d["metrica"].map(unid))
        )
    if not partes:
        return pd.DataFrame()
    return pd.concat(partes, ignore_index=True).assign(tema_codigo="deslocamento", subtema="Viagens a serviço")


def _deflator(periodos: pd.Series) -> tuple[pd.Series, str | None]:
    ipca = load_processed("pls_ipca")
    if ipca.empty:
        print("  atencao: sem IPCA processado -- valor_real = valor_nominal (rode `python run.py ipca`)")
        return pd.Series(1.0, index=periodos.index), None
    ipca = ipca.set_index("periodo")["indice"]
    ref = ipca.index.max()
    # meses depois do ultimo IPCA publicado ja estao a precos correntes
    fator = periodos.map(lambda p: ipca[ref] / ipca[p] if p in ipca.index else (1.0 if p > ref else np.nan))
    return fator, ref


def _evg() -> pd.DataFrame:
    """Cursos da Escola Virtual de Governo com a UFPB declarada pelo aluno (pls_evg),
    pelo mes da matricula. evg_pessoas_sust conta cada pessoa uma vez por ano, no mes
    da primeira certificacao em sustentabilidade -- a soma dos meses e o total de
    pessoas distintas do ano."""
    df = load_processed("pls_evg")
    if df.empty:
        return pd.DataFrame()
    df = df.assign(subtema=np.where(df["sustentabilidade"], "EVG · sustentabilidade", "EVG · demais temas"))
    cert = df[df["concluida"]]
    partes = [
        df.groupby(["periodo", "subtema"], as_index=False).size().rename(columns={"size": "valor"})
        .assign(metrica="evg_matriculas", unidade="un"),
        cert.groupby(["periodo", "subtema"], as_index=False).size().rename(columns={"size": "valor"})
        .assign(metrica="evg_certificados", unidade="un"),
        cert.groupby(["periodo", "subtema"], as_index=False)["carga_horaria"].sum()
        .rename(columns={"carga_horaria": "valor"}).assign(metrica="evg_horas_certificadas", unidade="h"),
    ]
    sust = cert[cert["sustentabilidade"] & cert["pessoa"].notna()].sort_values("periodo")
    primeira = sust.drop_duplicates(["ano", "pessoa"])
    if not primeira.empty:
        partes.append(primeira.groupby(["periodo", "subtema"], as_index=False).size()
                      .rename(columns={"size": "valor"}).assign(metrica="evg_pessoas_sust", unidade="pessoas"))
    return pd.concat(partes, ignore_index=True).assign(tema_codigo="capacitacao")


GRUPO_MODALIDADE = (("PREG", "Licitação"), ("CONCORR", "Licitação"), ("CONCURSO", "Licitação"), ("LEIL", "Licitação"),
                    ("DIALOGO", "Licitação"), ("DISPENSA", "Dispensa"), ("INEXIG", "Inexigibilidade"))
NIVEL_EDITAL = {"especifico": "critério específico", "preferencial": "só cláusula de preferência",
                "generico": "só menção genérica", "nenhum": "sem critério",
                "sem_texto": "sem documento legível", "sem_documento": "sem documento legível",
                "nao_lido": "documentos não lidos", "erro": "erro de leitura"}
LEGIVEL = {"especifico", "preferencial", "generico", "nenhum"}
MARCADORES_EDITAL = [  # (universo, marcador do universo, marcador do criterio, rotulo)
    ("Mão de obra exclusiva", "mao_obra_exclusiva", "cota_mulheres", "cota para mulheres"),
    ("Mão de obra exclusiva", "mao_obra_exclusiva", "mao_obra_local", "mão de obra local"),
    ("Alimentos", "alimentos", "agricultura_familiar", "agricultura familiar"),
    ("Obras e projetos", "obra_engenharia", "bim", "BIM"),
]


def _grupo_modalidade(nome: str) -> str:
    n = (nome or "").upper().replace("Ã", "A")
    return next((g for chave, g in GRUPO_MODALIDADE if n.startswith(chave)), "Outras")


def _compras() -> pd.DataFrame:
    """Contratacoes no PNCP (N10 e marcadores dos editais) e compras compartilhadas (N11)."""
    partes = []
    df = load_processed("pls_compras")
    if not df.empty:
        df = df.assign(grupo=df["modalidade"].map(_grupo_modalidade))
        df["subtema"] = df["grupo"] + " · " + df["nivel_sustentabilidade"].map(NIVEL_EDITAL).fillna("sem documento legível")
        g = df.groupby(["periodo", "subtema"])
        partes += [g.size().rename("valor").reset_index().assign(metrica="contratacoes_pncp", unidade="un"),
                   g["valor"].sum().reset_index().assign(metrica="contratacoes_pncp_valor", unidade="R$")]
        legivel = df["nivel_sustentabilidade"].isin(LEGIVEL)
        marc = df["marcadores"].map(lambda m: set(m) if m is not None else set())
        linhas = []
        lic = df[df["grupo"] == "Licitação"]
        for r in lic.itertuples():
            com = "com" if r.margem_preferencia else "sem"
            linhas.append((r.periodo, f"Licitações · {com} margem de preferência"))
        for universo, m_univ, m_crit, rot in MARCADORES_EDITAL:
            sel = df[marc.map(lambda s: m_univ in s)]
            for idx, r in sel.iterrows():
                if not legivel[idx]:
                    linhas.append((r["periodo"], f"{universo} · sem documento legível ({rot})"))
                else:
                    com = "com" if m_crit in marc[idx] else "sem"
                    linhas.append((r["periodo"], f"{universo} · {com} {rot}"))
        if linhas:
            partes.append(pd.DataFrame(linhas, columns=["periodo", "subtema"]).groupby(["periodo", "subtema"]).size()
                          .rename("valor").reset_index().assign(metrica="editais_marcadores", unidade="un"))
    comp = load_processed("pls_compras_compartilhadas")
    if not comp.empty:
        partes.append(comp.dropna(subset=["periodo"]).rename(columns={"tipo": "subtema"})
                      .groupby(["periodo", "subtema"]).size().rename("valor").reset_index()
                      .assign(metrica="compras_compartilhadas", unidade="un"))
    if not partes:
        return pd.DataFrame()
    return pd.concat(partes, ignore_index=True).assign(tema_codigo="contratacoes_pncp")


def _fornecedores() -> pd.DataFrame:
    """Pagamentos a PJ em contratacoes por categoria do fornecedor (modulo cnpj)."""
    df = load_processed("pls_pagamentos_pj")
    if df.empty or "subtema" not in df:
        return pd.DataFrame()
    return (df.groupby(["periodo", "subtema"], as_index=False)["valor"].sum()
            .assign(metrica="pago_fornecedores", unidade="R$", tema_codigo="fornecedores"))


def _fator(fatores: pd.DataFrame, item: str, periodo: str) -> tuple[float | None, bool]:
    """Fator vigente no mes; sem fator publicado para o periodo, o ultimo anterior (provisorio)."""
    f = fatores[fatores["item"] == item]
    vig = f[(f["inicio"] <= periodo) & (f["fim"] >= periodo)]
    if not vig.empty:
        return float(vig["valor"].iloc[0]), False
    antes = f[f["fim"] < periodo].sort_values("fim")
    return (float(antes["valor"].iloc[-1]), True) if not antes.empty else (None, True)


def _fatores_sin() -> dict[str, tuple[float, bool]]:
    """periodo -> (t CO2/MWh = kg CO2/kWh, provisorio), do modulo fator_sin. Mes publicado:
    fator do mes. Meses depois do ultimo publicado: fator anual do ultimo ano fechado, provisorio."""
    f = load_processed("pls_fator_sin")
    if f.empty:
        return {}
    out = {r.periodo: (float(r.fator_t_mwh), False) for r in f.itertuples()}
    anuais = f.dropna(subset=["fator_anual_t_mwh"])
    if not anuais.empty:
        anual = float(anuais.sort_values("periodo")["fator_anual_t_mwh"].iloc[-1])
        ano = int(f["ano"].max())
        for a in (ano, ano + 1):
            for m in range(1, 13):
                out.setdefault(f"{a}-{m:02d}", (anual, True))
    return out


def _gee(df: pd.DataFrame) -> pd.DataFrame:
    """Inventario de emissoes (kg CO2e) a partir do que o painel ja mede:
    escopo 1 = litros da frota x fator fossil (descontado o biocombustivel da mistura
    obrigatoria do mes), escopo 2 = kWh da rede x fator medio MENSAL do SIN (modulo fator_sin,
    planilha de inventarios do MCTI; sem ela, o anual de ref/fatores_gee.csv), escopo 3 =
    viagens aereas (ja calculado em pls_trechos). Demais fatores em ref/fatores_gee.csv."""
    from common import pls_map

    fatores = pls_map._read_ref("fatores_gee")
    fatores["valor"] = pd.to_numeric(fatores["valor"])
    partes, provisorios = [], set()
    comb = df[(df["metrica"] == "consumo_litros")]
    for r in comb.itertuples():
        if "diesel" in r.subtema:
            ef, _ = _fator(fatores, "diesel_a_co2", r.periodo)
            bio, _ = _fator(fatores, "biodiesel_no_diesel", r.periodo)
            kg, rot = r.valor * (1 - bio) * ef, "Escopo 1 · frota (diesel)"
        elif "gasolina" in r.subtema:
            ef, _ = _fator(fatores, "gasolina_a_co2", r.periodo)
            et, _ = _fator(fatores, "etanol_na_gasolina", r.periodo)
            kg, rot = r.valor * (1 - et) * ef, "Escopo 1 · frota (gasolina)"
        else:
            continue  # etanol hidratado: CO2 biogenico, fora do escopo 1
        partes.append({"periodo": r.periodo, "subtema": rot, "valor": kg})
    sin = _fatores_sin()
    for r in df[df["metrica"] == "consumo_kwh"].itertuples():
        ef, prov = sin.get(r.periodo, (None, True))
        if ef is None:  # sem a planilha do MCTI: fator anual de ref/fatores_gee.csv
            ef, prov = _fator(fatores, "energia_sin", r.periodo)
        if ef is None:
            continue
        if prov:
            provisorios.add(r.periodo[:4])
        partes.append({"periodo": r.periodo, "subtema": "Escopo 2 · energia elétrica", "valor": r.valor * ef})
    for r in df[df["metrica"] == "co2e_kg"].itertuples():
        partes.append({"periodo": r.periodo, "subtema": "Escopo 3 · viagens aéreas", "valor": r.valor})
    if provisorios:
        print(f"  atencao: fator do SIN provisorio para {', '.join(sorted(provisorios))}"
              " -- mes ainda nao publicado pelo MCTI (ou rode `python run.py fator_sin`)")
    if not partes:
        return pd.DataFrame()
    out = pd.DataFrame(partes).groupby(["periodo", "subtema"], as_index=False)["valor"].sum()
    return out.assign(metrica="emissoes_kgco2e", tema_codigo="emissoes", unidade="kg CO2e")


def _adesao_avn() -> pd.DataFrame:
    """E1-AVN-01: UGs da UFPB que pagaram o operador do Almoxarifado Virtual Nacional no ano / UGs da
    UFPB x 100. Um valor por ano, no ultimo mes com despesas carregadas (a soma do ano e o proprio %)."""
    from common import config
    from compras.avn import operadores

    d = load_processed("pls_despesas")
    if d.empty or "favorecido_codigo" not in d:
        return pd.DataFrame()
    pg = d[d["fase"] == "pagamento"]
    avn = pg[pg["favorecido_codigo"].isin(operadores())]
    ugs = set(config.UGS)
    linhas = []
    for ano, g in pg.groupby("ano"):
        com = set(avn[avn["ano"] == ano]["ug"]) & ugs
        linhas.append({"periodo": g["periodo"].max(), "tema_codigo": "material_consumo",
                       "subtema": "Adesão ao AVN (UGs)", "metrica": "adesao_avn_pct", "unidade": "%",
                       "valor": 100 * len(com) / len(ugs)})
    return pd.DataFrame(linhas)


def _area(subtemas: pd.Series) -> pd.Series:
    from common import pls_map

    area = pls_map._read_ref("area_construida")
    area["area_m2"] = pd.to_numeric(area["area_m2"])
    por_campus = area.groupby("campus")["area_m2"].sum()
    campus = subtemas.str.extract(r"^Campus (IV|III|II|I)$")[0]
    return campus.map(por_campus).fillna(area["area_m2"].sum())


def build() -> pd.DataFrame:
    partes = [p for p in (_despesas(), _itens(), _faturas(), _viagens(), _evg(), _fornecedores(), _compras(),
                          _adesao_avn()) if not p.empty]
    if not partes:
        return pd.DataFrame()
    base = pd.concat(partes, ignore_index=True)
    gee = _gee(base)
    df = pd.concat([base, gee], ignore_index=True).rename(columns={"valor": "valor_nominal"})
    df["subtema"] = df["subtema"].fillna("(sem subtema)")
    df["ano"] = df["periodo"].str[:4].astype(int)
    df["mes"] = df["periodo"].str[5:7].astype(int)

    fator, ref = _deflator(df["periodo"])
    monetario = df["unidade"] == "R$"
    df["valor_real"] = np.where(monetario, df["valor_nominal"] * fator, df["valor_nominal"])
    df["ref_ipca"] = np.where(monetario, ref, None)

    df["comunidade"], df["ano_comunidade"] = comunidade.por_ano(df["ano"], "comunidade")
    df["valor_real_per_capita"] = df["valor_real"] / df["comunidade"]
    df["area_m2"] = _area(df["subtema"])
    df["valor_por_m2"] = df["valor_real"] / df["area_m2"]
    df["servidores"], _ = comunidade.por_ano(df["ano"], "servidores")
    df["pct_servidores"] = 100 * df["valor_nominal"] / df["servidores"]
    return df.sort_values(["periodo", "tema_codigo", "subtema", "metrica"]).reset_index(drop=True)


def run(*, dry_run: bool = False, **_: object) -> None:
    df = build()
    if df.empty:
        print("Indicadores: nenhum dado processado ainda (rode os modulos de fonte antes)")
        return
    anual = df[df["metrica"] == "pago"].groupby("ano")["valor_real"].sum().round(2)
    report_counts("pago (inclui RP) real por ano (R$)", {str(a): float(v) for a, v in anual.items()})
    report_counts("documentos por metrica", df.groupby("metrica").size().to_dict())
    if not dry_run:
        save_processed(df, COLLECTION)
    replace_by(COLLECTION, df, "periodo", dry_run=dry_run)


if __name__ == "__main__":
    run()
