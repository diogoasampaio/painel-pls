"""Quantidade comprada de copos descartaveis, papel A4 e toner -> pls_itens_quantidade.

O item de empenho do Portal traz so o valor: quantidade e valor unitario vem
zerados. A quantidade sai do preco da compra:

  1. pncp      a descricao do item traz "Item compra: NNNNN". Entre os itens de
               numero NNNNN das compras por registro de precos da UFPB no PNCP
               (mesma familia de produto, compra publicada antes do empenho), vale
               o preco homologado do qual o valor empenhado e multiplo. Quantidade
               = valor / preco x unidades por embalagem (unidadeMedida do PNCP:
               "Pacote 100,00 UN", "Centena", "Resma"...)
  2. texto     quantidade escrita na descricao do item (papel e toner)
  3. multiplo  sem compra no PNCP (ata antiga ou de outro orgao): o preco e o
               maximo divisor comum dos valores do mesmo item no ano (>= 3
               empenhos); embalagem presumida (copo: pacote de 100)
  sem_preco    nenhum dos tres: o item fica fora da quantidade (continua no R$)
  avn          pedido do Almoxarifado Virtual Nacional atestado no processo de pagamento
               (compras/avn.py): quantidade do pedido x unidades no nome do produto

Mede AQUISICAO (empenho do item ou pedido do AVN, no mes da compra), nao consumo.

Unidades base: copos, resmas (500 folhas), cartuchos. Unidade do PNCP que nao
bate com o preco (copo a R$ 3,28 "Unidade") vai para
ref/itens_unidade_correcao.csv; sem correcao, preco por copo acima de R$ 0,50
presume pacote de 100 e o item sai marcado (unidade_presumida) para a saude.

Papel: so papel de impressao (A4, sulfite, oficio, resma). Canson, desenho,
diploma e blocos entram no R$ do tema, nao na quantidade de resmas.

Cache: itens e resultados de cada compra em data/raw/compras/itens/<ano>_<seq>.json;
compra publicada ha mais de 180 dias nao e consultada de novo.
"""

from __future__ import annotations

import math
import re
from datetime import date, datetime
from functools import reduce

import pandas as pd

from common import config
from common.mongo import replace_by
from common.storage import load_processed, raw_path, read_json, save_processed, write_json
from common.text import norm as normalize
from common.validation import report_counts
from compras.load_compras import CNPJ_UFPB, PNCP_API, _pncp

COLLECTION = "pls_itens_quantidade"
DIAS_CACHE = 180
TOLERANCIA = 0.005  # valor empenhado a ate 0,5% de um multiplo do preco

FAMILIAS = {
    "copo": {"regra": "copo_descartavel", "subtema": "Copos descartáveis", "base": "copos", "embalagem": 100,
             "item": r"\bcopos?\b", "pncp": r"\bcopo", "max_unit": 0.5},
    "papel": {"regra": "papel_a4", "subtema": "Papel A4 / resmas", "base": "resmas", "embalagem": 1,
              # papel de impressao, inclusive A3 e as marcas do AVN (Report, Chamex): resma de 500 folhas
              "item": r"papel (para )?impress|\bpapel\b.*\b(a4|a3|sulfite|oficio|report|chamex)\b|\bresmas?\b|tipo sulfite",
              "excluir": (r"diploma|bloco|canson|desenho|cartao|etiqueta|fotografic|adesiv|verge|couche|livro|copias|"
                          r"reproducao|kraft|embrulho|perfurador|pasta|envelope"),
              "pncp": r"papel (a4|sulfite|para impress|of[ií]cio)|resma|papel impress", "max_unit": 100.0},
    "toner": {"regra": "toner_cartucho", "subtema": "Toner e cartuchos", "base": "cartuchos", "embalagem": 1,
              "item": r"toner|cartuch", "pncp": r"toner|cartuch", "max_unit": None},
}
MATERIAL = re.compile(r"copa|cozinha|descart|expediente|papel|toner|cartuch|suprimento|impress|escrit[óo]rio|embalage",
                      re.I)
ITEM_COMPRA = re.compile(r"Item compra:\s*0*(\d+)", re.I)


# ------------------------------------------------------------------ unidades

def por_embalagem(unidade: str | None, familia: str) -> float | None:
    """Unidades base (copos, resmas, cartuchos) numa unidade de fornecimento do PNCP."""
    u = normalize(unidade or "")
    num = re.search(r"(\d+(?:[.,]\d+)?)", u)
    n = float(num.group(1).replace(".", "").replace(",", ".")) if num else None
    if familia == "papel":
        if "resma" in u:
            return n if n and "fl" not in u and "folha" not in u else 1.0
        if n and ("fl" in u or "folha" in u):
            return n / 500
        return 1.0 if u in ("unidade", "") else None
    if "centena" in u:
        return 100.0
    if "milheiro" in u:
        return 1000.0
    if n and re.search(r"\b(un|und|unidades?)\b", u):
        return n
    return 1.0 if u in ("unidade", "") else None


def correcoes() -> dict[tuple[str, int], float]:
    arq = config.REF_DIR / "itens_unidade_correcao.csv"
    if not arq.exists():
        return {}
    df = pd.read_csv(arq, sep=";", dtype=str, keep_default_na=False)
    return {(r.compra, int(r.item)): float(r.unidades_por_embalagem.replace(",", ".")) for r in df.itertuples()}


# ------------------------------------------------------------------ PNCP

def _compras_material() -> pd.DataFrame:
    c = load_processed("pls_compras")
    if c.empty:
        return c
    c = c[(c["srp"] == True) & c["objeto"].fillna("").str.contains(MATERIAL)]  # noqa: E712
    return c.assign(ano_compra=c["controle"].str.split("/").str[-1].astype(int),
                    seq=c["controle"].str.extract(r"-(\d+)/")[0].astype(int))


def _itens_compra(cli, ano: int, seq: int, publicada: str, hoje: date) -> dict:
    arq = raw_path("compras", "itens", f"{ano}_{seq}.json")
    if arq.exists():
        dias = (hoje - datetime.fromisoformat(str(publicada)[:10]).date()).days if publicada else 0
        cache = read_json(arq)
        if dias > DIAS_CACHE or cache.get("consultado") == hoje.isoformat():
            return cache
    base = f"{PNCP_API}/orgaos/{CNPJ_UFPB}/compras/{ano}/{seq}/itens"
    itens = cli.get_json(base, {"pagina": 1, "tamanhoPagina": 500}) or []
    padroes = re.compile("|".join(f["pncp"] for f in FAMILIAS.values()), re.I)
    sel = [{k: i.get(k) for k in ("numeroItem", "descricao", "unidadeMedida", "quantidade", "valorUnitarioEstimado",
                                  "situacaoCompraItemNome", "temResultado")}
           for i in itens if padroes.search(normalize(i.get("descricao") or ""))]
    resultados = {}
    for i in sel:
        if i.get("temResultado"):
            res = cli.get_json(f"{base}/{i['numeroItem']}/resultados") or []
            resultados[str(i["numeroItem"])] = [{"valorUnitarioHomologado": r.get("valorUnitarioHomologado"),
                                                 "quantidadeHomologada": r.get("quantidadeHomologada"),
                                                 "fornecedor": r.get("niFornecedor")} for r in res]
    dados = {"compra": f"{ano}/{seq}", "publicada": str(publicada)[:10], "itens": sel, "resultados": resultados,
             "consultado": hoje.isoformat()}
    write_json(arq, dados)
    return dados


def catalogo_pncp(hoje: date | None = None) -> pd.DataFrame:
    """Itens de copo, papel e toner das compras de material da UFPB no PNCP, um por preco homologado."""
    hoje = hoje or date.today()
    compras = _compras_material()
    if compras.empty:
        return pd.DataFrame()
    cli = _pncp()
    linhas = []
    for c in compras.itertuples():
        try:
            d = _itens_compra(cli, c.ano_compra, c.seq, c.data_publicacao, hoje)
        except Exception as e:  # compra que o PNCP nao devolve nao derruba o resto
            print(f"  PNCP {c.ano_compra}/{c.seq}: {type(e).__name__}: {e}")
            continue
        for i in d["itens"]:
            for r in d["resultados"].get(str(i["numeroItem"]), []):
                if r.get("valorUnitarioHomologado"):
                    linhas.append({"compra": d["compra"], "publicada": d["publicada"], "numero_item": int(i["numeroItem"]),
                                   "descricao_pncp": i["descricao"], "unidade_pncp": i["unidadeMedida"],
                                   "preco": float(r["valorUnitarioHomologado"])})
    print(f"  PNCP: {len(compras)} compras de material, {len(linhas)} preços homologados de copo, papel e toner "
          f"({cli.calls} chamadas)")
    return pd.DataFrame(linhas)


# ------------------------------------------------------------------ quantidade por item de empenho

def _familia(regras, descricao: str) -> str | None:
    d = normalize(descricao or "")
    for nome, f in FAMILIAS.items():
        if f["regra"] in list(regras if regras is not None else []) and re.search(f["item"], d) \
                and not (f.get("excluir") and re.search(f["excluir"], d)):
            return nome
    return None


def _multiplo(valor: float, preco: float) -> int | None:
    n = round(valor / preco)
    return n if n >= 1 and abs(valor - n * preco) <= max(0.02, TOLERANCIA * valor) else None


def calcular(itens: pd.DataFrame, cat: pd.DataFrame, corr: dict | None = None) -> pd.DataFrame:
    corr = corr or {}
    it = itens.assign(familia=[_familia(r, d) for r, d in zip(itens["regras_texto"], itens["descricao"])])
    it = it[it["familia"].notna() & (it["valor"] > 0)].copy()  # item de valor zero (servico de copias) nao e compra
    it["numero_item"] = it["descricao"].str.extract(ITEM_COMPRA)[0].astype(float)
    out = []
    for r in it.itertuples():
        f = FAMILIAS[r.familia]
        linha = {"empenho": r.empenho, "sequencial": r.sequencial, "periodo": r.periodo, "ano": r.ano, "mes": r.mes,
                 "ug": r.ug, "familia": r.familia, "subtema": f["subtema"], "unidade_base": f["base"],
                 "descricao": r.descricao, "valor": r.valor, "numero_item": r.numero_item,
                 "compra": None, "preco": None, "unidade_pncp": None, "por_embalagem": None, "embalagens": None,
                 "quantidade": None, "metodo": "sem_preco", "unidade_presumida": False}
        cand = cat[(cat["numero_item"] == r.numero_item) & (cat["publicada"] <= str(r.data)[:10])] \
            if not cat.empty and r.numero_item == r.numero_item else cat.iloc[0:0]
        if len(cand):
            cand = cand[cand["descricao_pncp"].map(lambda t: bool(re.search(f["pncp"], normalize(t))))]
        achou = None
        for c in cand.sort_values("publicada", ascending=False).itertuples():
            n = _multiplo(r.valor, c.preco)
            if n:
                achou = (c, n)
                break
        if achou:
            c, n = achou
            emb = corr.get((c.compra, int(c.numero_item)), por_embalagem(c.unidade_pncp, r.familia))
            presumida = False
            if emb is not None and f["max_unit"] and (c.compra, int(c.numero_item)) not in corr \
                    and c.preco / emb > f["max_unit"] and r.familia == "copo":
                emb, presumida = f["embalagem"], True
            linha.update(compra=c.compra, preco=c.preco, unidade_pncp=c.unidade_pncp, por_embalagem=emb, embalagens=n,
                         quantidade=n * emb if emb else None, metodo="pncp" if emb else "sem_preco",
                         unidade_presumida=presumida)
        elif r.familia != "copo" and r.quantidade_texto == r.quantidade_texto and r.quantidade_texto:
            linha.update(quantidade=float(r.quantidade_texto), metodo="texto")
        out.append(linha)
    df = pd.DataFrame(out)
    if df.empty:
        return df
    # multiplo: preco = MDC dos valores do mesmo item no ano, para o que nao achou compra
    sem = df["metodo"] == "sem_preco"
    for (_, _, desc), g in df[sem].groupby(["familia", "ano", "descricao"]):
        if len(g) < 3:
            continue
        mdc = reduce(math.gcd, (int(round(v * 100)) for v in g["valor"])) / 100
        fam = FAMILIAS[g["familia"].iloc[0]]
        if mdc < 0.5 or (fam["max_unit"] and fam["base"] != "copos" and mdc > fam["max_unit"]):
            continue
        n = (g["valor"] / mdc).round()
        df.loc[g.index, "preco"] = mdc
        df.loc[g.index, "embalagens"] = n
        df.loc[g.index, "por_embalagem"] = fam["embalagem"]
        df.loc[g.index, "quantidade"] = n * fam["embalagem"]
        df.loc[g.index, "metodo"] = "multiplo"
        df.loc[g.index, "unidade_presumida"] = fam["base"] == "copos"
    return df


# ------------------------------------------------------------------ pedidos do AVN

def unidades_no_nome(produto: str, familia: str) -> tuple[float, bool]:
    """(unidades base por item pedido, presumida?) a partir do nome do produto no AVN:
    'PCT 100UN', '500 Folhas', 'Caixa 10 Resmas', 'Kit 4UN'."""
    t = normalize(produto)
    if familia == "papel":
        m = re.search(r"(\d+)\s*resmas?\b", t)
        if m:
            return float(m.group(1)), False
        m = re.search(r"(\d[\d.]*)\s*(?:fls?|folhas)\b", t)
        if m:
            return float(m.group(1).replace(".", "")) / 500, False
        return 1.0, "resma" not in t
    m = (re.search(r"(?:pct|pacote|pc|cx|caixa|kit|c/|com)\s*(\d+)\s*(?:un|und|unid|unidades)?\b", t)
         or re.search(r"(\d+)\s*(?:un|und|unid|unidades)\b", t))
    if m:
        return float(m.group(1)), False
    return (float(FAMILIAS[familia]["embalagem"]), True) if familia == "copo" else (1.0, False)


def avn_quantidades() -> pd.DataFrame:
    """Copos, papel e toner dos pedidos do AVN (compras/avn.py), no mesmo formato de calcular()."""
    avn = load_processed("pls_avn_itens")
    if avn.empty:
        return pd.DataFrame()
    linhas = []
    for r in avn.itertuples():
        t = normalize(r.produto)
        fam = next((n for n, f in FAMILIAS.items() if re.search(f["item"], t)
                    and not (f.get("excluir") and re.search(f["excluir"], t))), None)
        if fam is None or r.quantidade != r.quantidade:
            continue
        f = FAMILIAS[fam]
        emb, presumida = unidades_no_nome(r.produto, fam)
        linhas.append({"empenho": None, "sequencial": None, "periodo": r.periodo, "ano": r.ano, "mes": r.mes, "ug": None,
                       "familia": fam, "subtema": f["subtema"], "unidade_base": f["base"], "descricao": r.produto,
                       "valor": r.valor, "numero_item": None, "compra": f"AVN pedido {r.pedido}", "preco": r.preco,
                       "unidade_pncp": None, "por_embalagem": emb, "embalagens": r.quantidade,
                       "quantidade": r.quantidade * emb, "metodo": "avn", "unidade_presumida": presumida})
    return pd.DataFrame(linhas)


def run(*, dry_run: bool = False, **_: object) -> None:
    itens = load_processed("pls_itens_empenho")
    if itens.empty:
        print("Quantidades: sem itens de empenho (rode `python run.py despesas`)")
        return
    df = calcular(itens, catalogo_pncp(), correcoes())
    # pedidos do AVN: empenhados como servico (3.3.90.39), nao se sobrepoem aos itens de material
    df = pd.concat([df, avn_quantidades()], ignore_index=True)
    if df.empty:
        print("Quantidades: nenhum item de copo, papel ou toner")
        return
    for fam, g in df.groupby("familia"):
        cob = g.groupby("metodo")["valor"].sum() / g["valor"].sum() * 100
        report_counts(f"{fam} - % do valor por método", {k: round(v, 1) for k, v in cob.items()})
        report_counts(f"{fam} - {FAMILIAS[fam]['base']} por ano", g.groupby("ano")["quantidade"].sum().round(0).to_dict())
    if not dry_run:
        save_processed(df, COLLECTION)
    replace_by(COLLECTION, df, "ano", dry_run=dry_run)


if __name__ == "__main__":
    run()
