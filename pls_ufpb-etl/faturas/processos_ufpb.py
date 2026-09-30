"""Base aberta de processos da UFPB -> conferencia e correcao do numero de
processo digitado no Portal da Transparencia.

Fonte: conjunto "Processos da UFPB" do portal de dados abertos
(dadosabertos.ufpb.br, Arquivo Central, atualizacao mensal): numero,
assunto, assunto detalhado, interessado, unidade de origem e situacao de
todos os processos ostensivos do SIPAC desde 2020 (~400 mil linhas, CSV de
~150 MB). O CSV vira data/raw/dadosabertos/processos_ufpb.parquet, so com
as colunas usadas, e e baixado de novo depois de VALIDADE_DIAS.

Numero do processo (NUP, Portaria Interministerial 11/2019):
23074.NNNNNN/AAAA-DV, DV = 98 - (radical+numero+ano x 100) mod 97.
Confere em 100% da base. O erro visto no Portal e sempre no numero, com o
DV certo ('2001657/2023-39' no lugar de '001657/2023-39'): o DV invalido
denuncia o erro, e o DV digitado mais o ano e o assunto acham o processo.
"""

from __future__ import annotations

import re
import time

import pandas as pd

from common.http import USER_AGENT
from common.storage import raw_path

API = "https://dadosabertos.ufpb.br/api/3/action/package_show?id=processos-da-ufpb"
CACHE = raw_path("dadosabertos", "processos_ufpb.parquet")
VALIDADE_DIAS = 30
COLUNAS = {"Num Processo": "numero", "Data Cadastro": "data_cadastro", "Status Processo": "situacao",
           "Unidade Origem": "unidade", "Interessado": "interessado", "Assunto": "assunto",
           "Assunto Detalhado": "assunto_detalhado"}
# texto (unidade + interessado + assuntos) que identifica o processo de cada tipo de fatura
PERFIL = {
    "energia": r"ENERGIA EL|ELETRICIDADE|ENERGISA",
    "agua": r"CAGEPA|[AÁ]GUA",
    "combustivel": r"PRIME CONSULTORIA|GOLDI|COMBUST|ABASTECIMENTO",
    "residuos": r"STERICYCLE|B-?GREEN|RES[IÍ]DUO|MEIO AMBIENTE",
}
# digitos de diferenca aceitos entre o numero digitado e o candidato
DISTANCIA_MAX = 2
_NUP = re.compile(r"(\d+)/(\d{4})-(\d{2})")


def dv(numero: str | int, ano: str | int, radical: str = "23074") -> str:
    return f"{98 - int(f'{radical}{int(numero):06d}{ano}') * 100 % 97:02d}"


def valido(processo: str) -> bool:
    m = _NUP.fullmatch(processo or "")
    return bool(m) and len(m.group(1)) <= 6 and dv(m.group(1), m.group(2)) == m.group(3)


def _baixar() -> pd.DataFrame:
    import requests

    s = requests.Session()
    s.headers["User-Agent"] = USER_AGENT
    recursos = s.get(API, timeout=60).json()["result"]["resources"]
    url = next(r["url"] for r in recursos if r["format"].upper() == "CSV" and "dicion" not in r["name"].lower())
    tmp = CACHE.with_suffix(".csv")
    tmp.parent.mkdir(parents=True, exist_ok=True)
    with s.get(url, timeout=600, stream=True) as r:
        r.raise_for_status()
        with open(tmp, "wb") as f:
            for bloco in r.iter_content(1 << 20):
                f.write(bloco)
    df = pd.read_csv(tmp, dtype=str, encoding="utf-8-sig", usecols=list(COLUNAS)).rename(columns=COLUNAS)
    tmp.unlink()
    m = df["numero"].str.extract(r"^\d+\.(\d+)/(\d{4})-(\d+)")
    df["num"], df["ano"], df["dv"] = m[0].str.zfill(6), m[1], m[2].str.zfill(2)
    df["processo"] = df["num"] + "/" + df["ano"] + "-" + df["dv"]
    df["situacao"] = df["situacao"].str.strip()
    df = df[df["num"].notna()].drop(columns="numero")
    df.to_parquet(CACHE, index=False)
    return df


def base(*, offline: bool = False) -> pd.DataFrame:
    """Base local; baixa de novo se passou de VALIDADE_DIAS. Falha no download usa o cache antigo."""
    velho = not CACHE.exists() or time.time() - CACHE.stat().st_mtime > VALIDADE_DIAS * 86400
    if velho and not offline:
        try:
            return _baixar()
        except Exception as e:  # rede/portal fora: segue com o que tiver
            print(f"  processos da UFPB: download falhou ({type(e).__name__}: {e})", flush=True)
    return pd.read_parquet(CACHE) if CACHE.exists() else pd.DataFrame()


def _distancia(a: str, b: str) -> int:
    """Damerau-Levenshtein (troca de dois digitos vizinhos conta 1)."""
    d = {(i, -1): i + 1 for i in range(-1, len(a))} | {(-1, j): j + 1 for j in range(-1, len(b))}
    for i in range(len(a)):
        for j in range(len(b)):
            d[i, j] = min(d[i - 1, j] + 1, d[i, j - 1] + 1, d[i - 1, j - 1] + (a[i] != b[j]))
            if i and j and a[i] == b[j - 1] and a[i - 1] == b[j]:
                d[i, j] = min(d[i, j], d[i - 2, j - 2] + 1)
    return d[len(a) - 1, len(b) - 1]


def candidatos(processo: str, tipo: str, b: pd.DataFrame) -> pd.DataFrame:
    """Processos do mesmo ano e do assunto do tipo com numero parecido, do mais provavel ao menos."""
    m = _NUP.fullmatch(processo or "")
    if not m or b.empty or tipo not in PERFIL:
        return pd.DataFrame()
    num, ano, digitado = m.groups()
    g = b[b["ano"] == ano]
    texto = (g["unidade"].fillna("") + " " + g["interessado"].fillna("") + " " + g["assunto"].fillna("") + " "
             + g["assunto_detalhado"].fillna("")).str.upper()
    g = g[texto.str.contains(PERFIL[tipo])]
    g = g.assign(distancia=[_distancia(num, x) for x in g["num"]], mesmo_dv=g["dv"] == digitado)
    return (g[g["distancia"] <= DISTANCIA_MAX]
            .sort_values(["mesmo_dv", "distancia"], ascending=[False, True])
            [["processo", "distancia", "mesmo_dv", "data_cadastro", "situacao", "assunto_detalhado"]])


def corrigir(processo: str, tipo: str, b: pd.DataFrame) -> tuple[str | None, list[str]]:
    """Numero certo quando so um candidato tem o DV digitado a ate DISTANCIA_MAX digitos; senao (None, candidatos)."""
    c = candidatos(processo, tipo, b)
    fortes = c[c["mesmo_dv"]] if not c.empty else c
    if len(fortes) == 1:
        return fortes["processo"].iloc[0], []
    return None, c["processo"].head(5).tolist() if not c.empty else []
