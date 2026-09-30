"""Meta projetada e projecao do ano corrente para os 15 indicadores do nucleo.

PROPOSTA, a validar pela Comissao do PLS: o painel mostra como esta a execucao
do ano em curso contra uma meta anual derivada de ref/metas_2026_projecao.csv.

Meta do ano (regra por indicador):
  reducao_anual    valor(ano_base) x (1 - p/100) ^ (ano - ano_base)
  reducao_vs_base  valor(ano_base) x (1 - p/100)
  minimo           p (na unidade do indicador)
  manter           valor(ano_base); ano_base "2023-2025" = media dos anos completos
  faixa            centro = media do ano_base; aceita +-p%

Projecao do ano (o ano ainda nao fechou):
  fluxo  (consumo, R$, kg, contagem, por pessoa, por m2): valor do ano anterior
         completo x (acumulado jan..M do ano / acumulado jan..M do ano anterior),
         M = ultimo mes do ano com dado da metrica.
         Mesmo periodo nos dois anos, entao a sazonalidade (ferias, verao) nao
         distorce. Sem ano anterior completo: acumulado x 12 / M
  razao  (percentual entre subtemas): o proprio acumulado do ano
  N15    (plano de acoes): o indice da data de referencia

Situacao: no_rumo (cumpre a meta), atencao (a ate 10% dela; na faixa, ate
1,5 x a tolerancia), fora_do_rumo, sem_dado.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from common import config
from metas import catalogo
from metas.load_metas import _automatico

TOLERANCIA_ATENCAO = 0.10


def regras() -> pd.DataFrame:
    df = pd.read_csv(config.REF_DIR / "metas_2026_projecao.csv", sep=";", dtype=str, keep_default_na=False)
    df["parametro"] = pd.to_numeric(df["parametro"].str.replace(",", "."), errors="coerce")
    return df.set_index("codigo")


def _anos_base(texto: str) -> list[int]:
    if not texto:
        return []
    ini, _, fim = texto.partition("-")
    return list(range(int(ini), int(fim or ini) + 1))


def meta_do_ano(regra, vals: dict[int, tuple[float, bool]], ano: int) -> tuple[float | None, tuple[float, float] | None]:
    """(meta, (min, max) quando a regra e faixa)."""
    p = regra.parametro
    if regra.regra == "minimo":
        return float(p), None
    anos = _anos_base(regra.ano_base)
    base = [vals[a][0] for a in anos if a in vals and vals[a][1]]
    if not base:
        return None, None
    ref = float(np.mean(base))
    if regra.regra == "reducao_anual":
        return ref * (1 - p / 100) ** (ano - anos[-1]), None
    if regra.regra == "reducao_vs_base":
        return ref * (1 - p / 100), None
    if regra.regra == "manter":
        return ref, None
    if regra.regra == "faixa":
        return ref, (ref * (1 - p / 100), ref * (1 + p / 100))
    raise ValueError(f"regra desconhecida em metas_2026_projecao.csv: {regra.regra}")


def _ultimo_mes(calc: dict, base: pd.DataFrame, ano: int) -> int:
    """ultimo mes do ano com dado da metrica (a fonte pode ter mes sem evento no meio, ex.: EVG)."""
    m = base[(base["metrica"] == calc["metrica"]) & (base["ano"] == ano)]["mes"]
    return int(m.max()) if len(m) else 0


def projetar(calc: dict | None, vals: dict[int, tuple[float, bool]], base: pd.DataFrame, ano: int,
             unidade: str = "") -> dict:
    """valor acumulado, meses com dado, projecao e metodo do ano."""
    atual = vals.get(ano)
    if atual is None:
        return {"valor_parcial": None, "meses": 0, "projecao": None, "metodo": "sem_dado"}
    valor, completo = atual
    if completo:
        return {"valor_parcial": valor, "meses": 12, "projecao": valor, "metodo": "ano_completo"}
    if calc is None:  # N15: fotografia na data de referencia
        return {"valor_parcial": valor, "meses": None, "projecao": valor, "metodo": "fotografia"}
    meses = _ultimo_mes(calc, base, ano)
    # percentual de estado (razao entre subtemas, adesao ao AVN): o acumulado do ano e a estimativa.
    # pct_servidores e fluxo (pessoas certificadas se acumulam no ano)
    if calc.get("razao_subtemas") or (unidade == "%" and calc.get("campo") != "pct_servidores"):
        return {"valor_parcial": valor, "meses": meses, "projecao": valor, "metodo": "acumulado"}
    anterior = vals.get(ano - 1)
    mesmo_periodo = base[base["mes"] <= meses] if meses else base.iloc[0:0]
    acum = _automatico(calc, mesmo_periodo)
    a0, a1 = acum.get(ano - 1), acum.get(ano)
    # o mesmo periodo do ano anterior so serve de base se tiver uma parte razoavel do ano (>= 1/4 do
    # esperado pelos meses): compra concentrada no fim do ano (papel em 2025) explodiria a razao
    base_ok = anterior and anterior[1] and a0 and a1 and a0 > 0 and anterior[0] > 0 \
        and a0 / anterior[0] >= 0.25 * meses / 12
    if base_ok:
        return {"valor_parcial": valor, "meses": meses, "projecao": anterior[0] * a1 / a0, "metodo": "mesmo_periodo"}
    if meses:
        return {"valor_parcial": valor, "meses": meses, "projecao": valor * 12 / meses, "metodo": "anualizado"}
    return {"valor_parcial": valor, "meses": 0, "projecao": None, "metodo": "sem_dado"}


def situacao(regra, meta: float | None, faixa: tuple[float, float] | None, proj: float | None) -> tuple[str, float | None]:
    """(situacao, alcance 0-100 da meta pela projecao)."""
    if meta is None or proj is None or meta == 0:
        return "sem_dado", None
    if regra.sentido == "faixa":
        desvio = abs(proj - meta) / meta
        tol = regra.parametro / 100
        sit = "no_rumo" if desvio <= tol else "atencao" if desvio <= 1.5 * tol else "fora_do_rumo"
        return sit, round(max(0.0, 100 * (1 - max(0.0, desvio - tol))), 1)
    razao = proj / meta if regra.sentido == "maior" else (meta / proj if proj else np.inf)
    sit = "no_rumo" if razao >= 1 else "atencao" if razao >= 1 - TOLERANCIA_ATENCAO else "fora_do_rumo"
    return sit, round(float(min(100.0, 100 * razao)), 1)


def linhas(nucleo: pd.DataFrame, cat: pd.DataFrame, vals_nucleo: dict, ano: int) -> list[dict]:
    """uma linha nivel=projecao por indicador do nucleo."""
    from common.storage import load_processed

    base = load_processed("pls_indicadores")
    tab = regras()
    c = cat.set_index("id")
    out = []
    for r in nucleo.itertuples():
        if r.codigo not in tab.index:
            continue
        regra = tab.loc[r.codigo]
        texto = c.loc[r.indicador_id, "calculo"] if r.indicador_id in c.index else r.calculo
        calc = catalogo.parse_calculo(texto) if texto else None
        calc = calc if calc and calc.get("tipo") == "ind" else None
        vals = vals_nucleo.get(r.codigo, {})
        meta, faixa = meta_do_ano(regra, vals, ano)
        proj = projetar(calc, vals, base, ano, r.unidade) if (calc or r.codigo == "N15") else \
            {"valor_parcial": None, "meses": 0, "projecao": None, "metodo": "sem_dado"}
        sit, alcance = situacao(regra, meta, faixa, proj["projecao"])
        out.append({"conjunto": "nucleo", "ano": ano, "nivel": "projecao", "codigo": r.codigo, **proj,
                    "meta_projetada": meta, "faixa_min": faixa[0] if faixa else None, "faixa_max": faixa[1] if faixa else None,
                    "regra": regra.regra, "parametro": regra.parametro, "ano_base": regra.ano_base or None,
                    "sentido": regra.sentido, "fundamento": regra.fundamento,
                    "situacao_projecao": sit, "alcance_projecao": alcance})
    return out
