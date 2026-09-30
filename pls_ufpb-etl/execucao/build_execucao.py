"""Indice sintetico de execucao do PLS e distribuicao dos indicadores por faixa -> pls_execucao.

Roda depois de `metas` e `acoes`. Para cada conjunto de indicadores e ano:

  conjunto   plano   os 34 indicadores do PLS UFPB 2025-2029 (ids E*)
             nucleo  os 15 indicadores do nucleo mais os complementares (N16 em
                     diante, grupo=complementar em ref/nucleo_pls.csv); os de
                     no_indice=nao aparecem no painel mas ficam fora do indice -- o
                     conjunto do painel geral. Meta e valor vem do
                     indicador_catalogo de cada Nxx; sem id no catalogo, o
                     valor sai do `calculo` do proprio nucleo (N04, N05). N15
                     (cumprimento das acoes) aparece como indicador e e o
                     componente de acoes do indice, fora do componente de metas

  alcance    de cada indicador no ano (0 a 100, em pls_metas): quanto da meta
             foi cumprido -- ver metas.load_metas.alcance
  faixa      ref/faixas_execucao.csv: atingida (100), proxima (75+),
             progresso (50+), distante (<50), e as sem alcance:
             nao_avaliavel (linha de base / ano parcial), sem_dado, sem_meta

  indice_metas      media do alcance dos indicadores avaliados; com
                    agregacao_metas=eixo, media por eixo e depois media dos
                    eixos (cada eixo pesa igual)
  indice_acoes      indice de cumprimento do plano de acoes (modulo acoes,
                    N15) -- so no ano da data de referencia (e fotografia)
  ano_metas         ano de onde vem o indice_metas. No ano corrente as metas
                    ainda nao sao avaliaveis (ano parcial): vale o ultimo ano
                    avaliado, para o indice atual combinar as metas mais
                    recentes com as acoes do ciclo em curso
  indice_sintetico  peso_metas x indice_metas + peso_acoes x indice_acoes
                    (ref/indice_execucao.csv); faltando um componente, o
                    outro vale sozinho e `componentes` diz qual entrou
  cobertura_pct     indicadores avaliados / indicadores com meta -- indice
                    alto com cobertura baixa diz pouco sobre o plano

Linhas: nivel=geral (1 por conjunto e ano), nivel=eixo, nivel=indicador
(a faixa de cada indicador, para o painel listar), nivel=faixa (definicao
de ref/faixas_execucao.csv), nivel=parametros (ref/indice_execucao.csv),
nivel=historico (serie anual do nucleo) e nivel=projecao (meta projetada e
projecao do ano corrente de cada indicador do nucleo, execucao/projecao.py).
"""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd

from common import config
from common.mongo import replace_by
from common.storage import load_processed, save_processed
from common.validation import report_counts
from metas import catalogo
from execucao import projecao
from metas.load_metas import _automatico, faixas

COLLECTION = "pls_execucao"
SEM_ALCANCE = ("nao_avaliavel", "sem_dado", "sem_meta")


def parametros() -> dict:
    df = pd.read_csv(config.REF_DIR / "indice_execucao.csv", sep=";", dtype=str)
    p = dict(zip(df["parametro"], df["valor"]))
    return {"peso_metas": float(p["peso_metas"]), "peso_acoes": float(p["peso_acoes"]),
            "agregacao_metas": p.get("agregacao_metas", "eixo"), "primeiro_ano": int(p["primeiro_ano"])}


def conjuntos(cat: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """indicadores de cada conjunto: codigo exibido, indicador_id, eixo, nome, meta."""
    plano = cat[cat["id"].str.startswith("E")]
    out = {"plano": pd.DataFrame({"codigo": plano["id"], "indicador_id": plano["id"], "eixo_pls": plano["eixo_pls"],
                                  "indicador": plano["indicador"], "tipo_meta": plano["tipo_meta"],
                                  "unidade": plano["unidade"], "meta": plano["meta"]})}
    nuc = pd.read_csv(config.REF_DIR / "nucleo_pls.csv", sep=";", dtype=str, keep_default_na=False)
    ids = nuc["indicador_catalogo"].str.split("|").str[0]
    c = cat.set_index("id")
    tipo = ids.map(c["tipo_meta"]).fillna("acompanhamento")
    out["nucleo"] = pd.DataFrame({
        "codigo": nuc["codigo"], "indicador_id": ids.replace("", None), "eixo_pls": nuc["eixo_pls"],
        "indicador": nuc["indicador"], "tipo_meta": tipo, "unidade": nuc["unidade"], "formula": nuc["formula"],
        "meta": ids.map(c["meta"]).where(tipo != "acompanhamento", ""), "meta_sugerida": nuc.get("meta_sugerida", ""),
        "automacao": nuc["situacao"], "fonte": nuc["fonte"], "calculo": nuc["calculo"],
        "unidade_catalogo": ids.map(c["unidade"]),
        "polaridade": nuc["codigo"].map(polaridades()).fillna("neutro"),
        # nucleo (N01-N15) ou complementar (N16 em diante); no_indice=False fica fora do indice sintetico
        "grupo": nuc["grupo"] if "grupo" in nuc else "nucleo",
        "no_indice": (nuc["no_indice"] if "no_indice" in nuc else pd.Series("sim", index=nuc.index)).ne("nao"),
    }).reset_index(drop=True)
    fichas = _fichas()
    for campo in ("o_que_mede", "periodicidade", "responsavel"):
        out["nucleo"][campo] = out["nucleo"]["codigo"].map(fichas.get(campo, {}))
    return out


def _fichas() -> dict[str, dict[str, str]]:
    """campo -> {codigo: texto} de ref/fichas_nucleo.csv (o que mede, periodicidade, responsavel)."""
    arq = config.REF_DIR / "fichas_nucleo.csv"
    if not arq.exists():
        return {}
    f = pd.read_csv(arq, sep=";", dtype=str, keep_default_na=False).set_index("codigo")
    return {c: f[c].to_dict() for c in f.columns}


def polaridades() -> dict[str, str]:
    """codigo -> menor | maior | neutro, do texto de ref/fichas_nucleo.csv ("Quanto menor, melhor"...).
    Neutro: o sentido depende do contexto (N04, N06, N14) e o painel nao pinta a variacao."""
    arq = config.REF_DIR / "fichas_nucleo.csv"
    if not arq.exists():
        return {}
    f = pd.read_csv(arq, sep=";", dtype=str, keep_default_na=False)
    txt = f["polaridade"].str.lower()
    pol = txt.map(lambda t: "menor" if t.startswith("quanto menor") else "maior" if t.startswith("quanto maior") else "neutro")
    return dict(zip(f["codigo"], pol))


def valores_nucleo(ind: pd.DataFrame, metas: pd.DataFrame, acoes: pd.DataFrame) -> dict[str, dict[int, tuple[float, bool]]]:
    """codigo -> {ano: (valor, ano_completo)} na unidade do nucleo."""
    base = load_processed("pls_indicadores")
    out: dict[str, dict[int, tuple[float, bool]]] = {}
    for r in ind.itertuples():
        vals: dict[int, tuple[float, bool]] = {}
        if r.indicador_id and not metas.empty:
            for m in metas[metas["indicador_id"] == r.indicador_id].itertuples():
                vals[int(m.ano)] = (float(m.valor), bool(m.ano_completo))
            if r.unidade.startswith("tCO") and str(r.unidade_catalogo).startswith("kg"):
                vals = {a: (v / 1000, c) for a, (v, c) in vals.items()}
        elif r.calculo and not base.empty:
            serie = _automatico(catalogo.parse_calculo(r.calculo), base)
            meses = serie.attrs.get("meses", {})
            vals = {int(a): (float(v), meses.get(a, 0) == 12) for a, v in serie.items()}
        elif r.codigo == "N15" and not acoes.empty and acoes["indice_cumprimento"].notna().any():
            ano = int(str(acoes["data_referencia"].iloc[0])[:4])
            vals = {ano: (float(acoes["indice_cumprimento"].dropna().iloc[0]), False)}
        out[r.codigo] = vals
    return out


def _faixa_no_ano(ind: pd.DataFrame, metas: pd.DataFrame, ano: int) -> pd.DataFrame:
    m = metas[metas["ano"] == ano].set_index("indicador_id")[["alcance_pct", "faixa", "valor", "situacao"]]
    df = ind.join(m, on="indicador_id")
    sem_linha = df["faixa"].isna()
    df.loc[sem_linha, "faixa"] = np.where(df.loc[sem_linha, "tipo_meta"] == "acompanhamento", "sem_meta", "sem_dado")
    return df


def _indice_metas(df: pd.DataFrame, agregacao: str) -> float | None:
    av = df.dropna(subset=["alcance_pct"])
    if av.empty:
        return None
    if agregacao == "eixo":
        return round(float(av.groupby("eixo_pls")["alcance_pct"].mean().mean()), 1)
    return round(float(av["alcance_pct"].mean()), 1)


def _resumo(df: pd.DataFrame, codigos: list[str], agregacao: str) -> dict:
    com_meta = df[df["faixa"] != "sem_meta"]
    avaliados = df["alcance_pct"].notna().sum()
    out = {"n_indicadores": len(df), "n_com_meta": len(com_meta), "n_avaliados": int(avaliados),
           "cobertura_pct": round(100 * avaliados / len(com_meta), 1) if len(com_meta) else None,
           "indice_metas": _indice_metas(df, agregacao)}
    out.update({f"faixa_{c}": int((df["faixa"] == c).sum()) for c in codigos})
    return out


def _sintetico(indice_metas, indice_acoes, p: dict) -> tuple[float | None, str]:
    partes = [(indice_metas, p["peso_metas"], "metas"), (indice_acoes, p["peso_acoes"], "acoes")]
    partes = [(v, w, n) for v, w, n in partes if v is not None and not pd.isna(v) and w > 0]
    if not partes:
        return None, ""
    total = sum(w for _, w, _ in partes)
    return round(sum(v * w for v, w, _ in partes) / total, 1), "+".join(n for _, _, n in partes)


def build(hoje: date | None = None) -> pd.DataFrame:
    hoje = hoje or date.today()
    p = parametros()
    cat = catalogo.carregar()
    metas = load_processed("pls_metas")
    acoes = load_processed("pls_acoes")
    codigos = faixas()["codigo"].tolist()
    indice_acoes, ano_acoes = None, None
    if not acoes.empty and "indice_cumprimento" in acoes:
        indice_acoes = acoes["indice_cumprimento"].dropna().iloc[0] if acoes["indice_cumprimento"].notna().any() else None
        ano_acoes = int(str(acoes["data_referencia"].iloc[0])[:4])
    ultimo = int(metas["ano"].max()) if not metas.empty else hoje.year
    anos = range(p["primeiro_ano"], max(ultimo, hoje.year) + 1)

    linhas = []
    todos = conjuntos(cat)
    vals_nucleo = valores_nucleo(todos["nucleo"], metas, acoes)
    for nome, ind in todos.items():
        ultimo_metas: tuple[int, float] | None = None
        for ano in anos:
            df = _faixa_no_ano(ind, metas, ano) if not metas.empty else ind.assign(alcance_pct=None, faixa="sem_dado")
            acoes_ano = indice_acoes if ano == ano_acoes else None
            # indice e contagens so com os indicadores que entram no indice (no plano, todos)
            no_indice = df[df["no_indice"]] if "no_indice" in df else df
            geral = _resumo(no_indice, codigos, p["agregacao_metas"])
            metas_ano, ano_metas = geral["indice_metas"], ano
            if metas_ano is not None:
                ultimo_metas = (ano, metas_ano)
            elif ano == ano_acoes and ultimo_metas:
                ano_metas, metas_ano = ultimo_metas
            if metas_ano is None:
                ano_metas = None
            sint, comp = _sintetico(metas_ano, acoes_ano, p)
            linhas.append({"conjunto": nome, "ano": ano, "nivel": "geral", "eixo_pls": None, **geral,
                           "indice_acoes": acoes_ano, "indice_sintetico": sint, "componentes": comp,
                           "indice_metas_usado": metas_ano, "ano_metas": ano_metas,
                           "ano_fechado": ano < hoje.year})
            for eixo, g in no_indice.groupby("eixo_pls"):
                linhas.append({"conjunto": nome, "ano": ano, "nivel": "eixo", "eixo_pls": eixo,
                               **_resumo(g, codigos, "indicador")})
            for r in df.itertuples():
                if nome == "nucleo":
                    valor, completo = vals_nucleo.get(r.codigo, {}).get(ano, (None, None))
                else:
                    valor, completo = (r.valor if r.valor == r.valor else None), None
                extra = {k: getattr(r, k) for k in ("formula", "meta_sugerida", "automacao", "fonte", "polaridade",
                                                        "o_que_mede", "periodicidade", "responsavel", "grupo",
                                                        "no_indice") if hasattr(r, k)}
                linhas.append({"conjunto": nome, "ano": ano, "nivel": "indicador", "eixo_pls": r.eixo_pls,
                               "codigo": r.codigo, "indicador_id": r.indicador_id, "indicador": r.indicador,
                               "tipo_meta": r.tipo_meta, "alcance_pct": r.alcance_pct, "faixa": r.faixa,
                               "situacao": r.situacao if isinstance(r.situacao, str) else None,
                               "valor": valor, "ano_completo": completo, "unidade": r.unidade, "meta": r.meta, **extra})
    # serie anual completa dos 15 do nucleo (desde o 1o ano com dado, antes do indice existir):
    # a pagina inicial do painel mostra a evolucao de cada indicador
    for codigo, vals in vals_nucleo.items():
        for ano, (valor, completo) in sorted(vals.items()):
            if valor == valor:
                linhas.append({"conjunto": "nucleo", "ano": ano, "nivel": "historico", "codigo": codigo,
                               "valor": valor, "ano_completo": completo})
    # meta projetada e projecao do ano corrente (proposta a validar, execucao/projecao.py)
    linhas.extend(projecao.linhas(todos["nucleo"], cat, vals_nucleo, hoje.year))
    # definicao das faixas e parametros do indice junto, para a API nao repetir rotulos
    for nome in todos:
        for r in faixas().itertuples():
            linhas.append({"conjunto": nome, "nivel": "faixa", "codigo": r.codigo, "faixa": r.faixa,
                           "alcance_minimo": r.alcance_minimo, "ordem": r.ordem, "descricao": r.descricao})
        linhas.append({"conjunto": nome, "nivel": "parametros", **{k: v for k, v in p.items()}})
    df = pd.DataFrame(linhas)
    df["ano"] = df["ano"].astype("Int64")
    df["chave"] = df["conjunto"]
    df["data_referencia"] = hoje.isoformat()
    return df


def run(*, dry_run: bool = False, **_: object) -> None:
    df = build()
    g = df[df["nivel"] == "geral"]
    for r in g.itertuples():
        print(f"  {r.conjunto:<6} {r.ano}: sintetico {r.indice_sintetico} ({r.componentes or '-'}) | metas {r.indice_metas} "
              f"(de {r.ano_metas}) | acoes {r.indice_acoes} | avaliados {r.n_avaliados}/{r.n_com_meta} com meta | "
              f"atingida {r.faixa_atingida} proxima {r.faixa_proxima} progresso {r.faixa_progresso} distante {r.faixa_distante}")
    report_counts("execucao - linhas por nivel", df.groupby("nivel").size().to_dict())
    if not dry_run:
        save_processed(df, COLLECTION)
    replace_by(COLLECTION, df, "chave", dry_run=dry_run)


if __name__ == "__main__":
    run()
