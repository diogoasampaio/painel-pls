"""Classificacao de despesas nos temas do PLS a partir das tabelas em ref/.

- natureza de despesa (8 digitos: categoria+grupo+modalidade+elemento+
  subelemento, ex. 33903943) -> tema/subtema, por prefixo mais longo. Uma
  linha de 6 digitos (339014) cobre todos os subitens do elemento.
- descricao do item de empenho -> regras de texto (papel A4, copo
  descartavel, LED, fotovoltaica, residuos...).

A API do Portal devolve categoria/grupo/modalidade/elemento ora como nome
("Outros Servicos de Terceiros - Pessoa Juridica"), ora com codigo na
frente; `codigo_de` aceita os dois formatos.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache

import pandas as pd

from . import config
from .text import leading_code, norm

NAO_CLASSIFICADO = "nao_classificado"


def _read_ref(name: str) -> pd.DataFrame:
    return pd.read_csv(config.REF_DIR / f"{name}.csv", sep=";", dtype=str, keep_default_na=False)


@lru_cache
def temas() -> pd.DataFrame:
    return _read_ref("temas_pls")


@lru_cache
def acoes() -> dict[str, str]:
    """Acoes orcamentarias acompanhadas pelo PLS (ref/acoes_pls.csv): codigo -> tema.
    Todas as naturezas da acao entram, mesmo as fora do mapeamento de naturezas."""
    arq = config.REF_DIR / "acoes_pls.csv"
    if not arq.exists():
        return {}
    df = _read_ref("acoes_pls")
    return dict(zip(df["acao"].str.strip(), df["tema_codigo"].str.strip()))


@lru_cache
def mapeamento() -> pd.DataFrame:
    df = _read_ref("mapeamento_natureza_pls")
    df["natureza"] = df["natureza"].str.strip()
    # prefixo mais longo primeiro: 33903943 vence 339039 se ambos existirem
    return df.sort_values("natureza", key=lambda s: s.str.len(), ascending=False).reset_index(drop=True)


@lru_cache
def regras_texto() -> list[tuple[str, str, str, re.Pattern, str]]:
    df = _read_ref("regras_texto_pls")
    return [
        (r.regra, r.tema_codigo, r.subtema, re.compile(r.padrao), r.unidade)
        for r in df.itertuples()
    ]


@lru_cache
def _nomes_por_nivel() -> dict[str, dict[str, str]]:
    df = _read_ref("elementos_despesa")
    out: dict[str, dict[str, str]] = {}
    for r in df.itertuples():
        out.setdefault(r.nivel, {})[norm(r.nome)] = r.codigo
    return out


_PAD = {"categoria": 1, "grupo": 1, "modalidade": 2, "elemento": 2}


def codigo_de(nivel: str, valor: object) -> str | None:
    code = leading_code(valor)
    if code is None:
        key = norm(valor)
        if not key:
            return None
        nomes = _nomes_por_nivel().get(nivel, {})
        code = nomes.get(key)
        if code is None:
            # tolera variacoes de redacao ("Diarias - Pessoal Civil" x "Diarias - Civil")
            code = next((c for n, c in nomes.items() if key.startswith(n) or n.startswith(key)), None)
    return code.zfill(_PAD[nivel]) if code else None


def natureza6(categoria: object, grupo: object, modalidade: object, elemento: object) -> str | None:
    partes = [
        codigo_de("categoria", categoria),
        codigo_de("grupo", grupo),
        codigo_de("modalidade", modalidade),
        codigo_de("elemento", elemento),
    ]
    return "".join(partes) if all(partes) else None  # type: ignore[arg-type]


def natureza8(nat6: str | None, subitem: object) -> str | None:
    """Junta o subelemento (que pode vir como '43', '39.43', '33903943' ou
    '43 - SERVICOS DE ENERGIA') ao prefixo de 6 digitos.
    """
    m = re.match(r"\s*([\d.]+)", str(subitem or ""))
    digits = re.sub(r"\D", "", m.group(1)) if m else ""
    if len(digits) >= 8:
        return digits[-8:]
    if nat6 and 1 <= len(digits) <= 2:
        return nat6 + digits.zfill(2)
    if nat6 and len(digits) == 4 and digits[:2] == nat6[-2:]:
        return nat6 + digits[2:]
    return None


@dataclass(frozen=True)
class Classificacao:
    tema_codigo: str
    subtema: str | None
    natureza_mapeada: str | None


def classificar_natureza(natureza: str | None) -> Classificacao:
    if natureza:
        for r in mapeamento().itertuples():
            if natureza.startswith(r.natureza):
                return Classificacao(r.tema_codigo, r.subtema, r.natureza)
    return Classificacao(NAO_CLASSIFICADO, None, None)


def elemento_relevante(nat6: str | None) -> bool:
    """Documento de liquidacao/pagamento merece a chamada extra de
    empenhos-impactados? Sem natureza resolvida, sim (melhor gastar uma
    chamada do que perder despesa).
    """
    if not nat6:
        return True
    return any(p.startswith(nat6) or nat6.startswith(p) for p in mapeamento()["natureza"])


def classificar_texto(descricao: object) -> list[dict[str, str]]:
    texto = norm(descricao)
    return [
        {"regra": regra, "tema_codigo": tema, "subtema": sub, "unidade": un}
        for regra, tema, sub, padrao, un in regras_texto()
        if padrao.search(texto)
    ]


_QTD = re.compile(r"\b(?:quantidade|qtde?|qtd)\.?\s*[:=]?\s*([\d.]+(?:,\d+)?)")


def quantidade_no_texto(descricao: object) -> float | None:
    """Itens de empenho do SIAFI costumam trazer 'QUANTIDADE: 500' no texto."""
    m = _QTD.search(norm(descricao))
    if not m:
        return None
    try:
        return float(m.group(1).replace(".", "").replace(",", "."))
    except ValueError:
        return None
