"""Cursos e participantes da Escola Virtual de Governo (EVG/ENAP) -> pls_evg.

Fonte: conjunto "Dados sobre cursos e participantes na plataforma da Escola
Virtual de Governo" no dados.gov.br -- um CSV por bimestre (~50 a 360 MB,
~600 mil matriculas do pais inteiro), hospedado no Google Drive da ENAP. Os
ids dos arquivos ficam em ref/evg_recursos.csv (o dados.gov.br so lista os
recursos com login/JS; atualize a tabela quando sair um bimestre novo).

A UFPB aparece pelo campo `instituicao`, que o proprio aluno declara na
"experiencia profissional mais recente" do cadastro (lista padronizada:
"Universidade Federal da Paraiba"). Nao ha como confirmar que a pessoa e
servidor: pode incluir estudante, terceirizado ou ex-servidor, e a maioria
dos alunos nao preenche o campo. E um indicador aproximado.

Cada arquivo e lido em streaming e so as matriculas da UFPB ficam em
data/raw/evg/<ano>_<bimestre>.json. LGPD: os arquivos ate 2024 trazem nome e
CPF parcial -- sao descartados na leitura; fica so `pessoa`, um hash com sal
local (variavel EVG_SAL ou data/raw/evg/_sal.txt, fora do git) usado apenas para contar pessoas distintas no ano. De
2025 em diante a propria ENAP ja publica `codigo_pessoa` anonimizado.

Formatos vistos: jan-fev/2023 com ';' e datas dd/mm/aaaa; depois '|' e ISO;
2026 com outra ordem de colunas -- a leitura e pelo nome do cabecalho.

pls_evg  1 doc por matricula: periodo (mes da matricula), curso, tematica,
         carga horaria, situacao, concluida, sustentabilidade, pessoa.
         Situacao e a da data de extracao do bimestre: matricula do fim do
         bimestre pode aparecer "Nao Concluido" e concluir depois.
"""

from __future__ import annotations

import hashlib
import os
import secrets
import unicodedata
from functools import lru_cache
from itertools import chain

import pandas as pd
import requests

from common import config
from common.mongo import replace_by
from common.periodo import Janela
from common.storage import raw_path, read_json, save_processed, write_json
from common.validation import report_counts

COLLECTION = "pls_evg"
URL = "https://drive.usercontent.google.com/download?id={id}&export=download&confirm=t"
INSTITUICAO_UFPB = "UNIVERSIDADE FEDERAL DA PARAIBA"
CAMPOS = ["cod_matricula", "dt_matricula", "cod_curso", "nome_curso", "carga_horaria", "tematica", "conteudista",
          "modalidade_turma", "dt_inicio", "dt_fim", "sit_matricula", "poder", "esfera"]


CABECALHO_27 = ["cod_matricula", "dt_matricula", "nacionalidade", "cod_turma", "nome_turma", "modalidade_turma", "cod_curso",
                "nome_curso", "carga_horaria", "dt_inicio_insc", "dt_fim_insc", "dt_inicio", "dt_fim", "sit_turma",
                "instituicao", "municipio_pessoa", "uf_pessoa", "conteudista", "tematica", "municipio_servidor",
                "codigo_pessoa", "sexo", "idade", "sit_matricula", "poder", "esfera", "uf_servidor"]


def _norm(s: str) -> str:
    return unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().upper().strip()


def recursos() -> pd.DataFrame:
    return pd.read_csv(config.REF_DIR / "evg_recursos.csv", sep=";", dtype={"ano": int, "bimestre": int, "drive_id": str})


@lru_cache
def _sal() -> str:
    """Sal do hash: EVG_SAL ou um sorteado na primeira execucao e guardado junto
    do cache (o mesmo sal mantem o hash estavel entre execucoes)."""
    if os.environ.get("EVG_SAL"):
        return os.environ["EVG_SAL"]
    arq = raw_path("evg", "_sal.txt")
    if not arq.exists():
        arq.parent.mkdir(parents=True, exist_ok=True)
        arq.write_text(secrets.token_hex(16), encoding="utf-8")
    return arq.read_text(encoding="utf-8").strip()


def _pessoa(linha: dict) -> str | None:
    """Identificador so para contar pessoas distintas: codigo_pessoa da ENAP ou
    hash (com sal) de CPF parcial + nome -- nome e CPF nao saem daqui."""
    if linha.get("codigo_pessoa"):
        return linha["codigo_pessoa"]
    base = (linha.get("cpf") or "") + "|" + _norm(linha.get("nome") or "")
    if base == "|":
        return None
    return hashlib.sha256((_sal() + base).encode()).hexdigest()[:20]


def filtrar_ufpb(linhas) -> list[dict]:
    """Linhas de texto do CSV (cabecalho primeiro) -> matriculas da UFPB, sem dado pessoal."""
    it = iter(linhas)
    cab = next(it).rstrip("\r\n")
    sep = "|" if cab.count("|") > cab.count(";") else ";"
    cols = [c.strip().lstrip("﻿").lower() for c in cab.split(sep)]  # mai-jun/2023 comeca com BOM
    if "cod_matricula" not in cols:
        # nov-dez/2024 veio sem cabecalho: layout de 27 colunas do fim de 2024/2025;
        # a primeira linha ja e dado
        cols = CABECALHO_27
        it = chain([cab], it) if len(cab.split(sep)) == len(cols) else it
    ix = {c: i for i, c in enumerate(cols)}
    out = []
    for texto in it:
        p = texto.rstrip("\r\n").split(sep)
        if len(p) < len(cols):
            continue
        if _norm(p[ix["instituicao"]]) != INSTITUICAO_UFPB:
            continue
        linha = {c: p[i].strip() for c, i in ix.items()}
        reg = {c: linha.get(c) or None for c in CAMPOS}
        reg["pessoa"] = _pessoa(linha)
        out.append(reg)
    return out


def _linhas(resp):
    for bruta in resp.iter_lines():
        try:
            yield bruta.decode("utf-8")
        except UnicodeDecodeError:
            yield bruta.decode("latin-1")


def extract(janela: Janela, offline: bool = False) -> tuple[list[dict], dict]:
    info = {"arquivos": 0, "do_cache": 0, "baixados": 0}
    regs: list[dict] = []
    for r in recursos().itertuples():
        if r.ano not in janela.anos():
            continue
        info["arquivos"] += 1
        cache = raw_path("evg", f"{r.ano}_{r.bimestre}.json")
        if cache.exists():
            dados = read_json(cache)
            info["do_cache"] += 1
        elif offline:
            continue
        else:
            print(f"  EVG {r.titulo}: lendo em streaming...", flush=True)
            with requests.get(URL.format(id=r.drive_id), stream=True, timeout=600) as resp:
                resp.raise_for_status()
                dados = {"titulo": r.titulo, "matriculas": filtrar_ufpb(_linhas(resp))}
            write_json(cache, dados)
            info["baixados"] += 1
            print(f"    {len(dados['matriculas'])} matriculas da UFPB", flush=True)
        regs += [{**m, "ano_arquivo": r.ano, "bimestre": r.bimestre} for m in dados["matriculas"]]
    return regs, info


def _data(s: pd.Series) -> pd.Series:
    iso = pd.to_datetime(s, format="%Y-%m-%d %H:%M:%S", errors="coerce")
    br = pd.to_datetime(s, format="%d/%m/%Y %H:%M", errors="coerce")
    return iso.fillna(br).fillna(pd.to_datetime(s, errors="coerce", dayfirst=True))


def _sustentavel(df: pd.DataFrame) -> pd.Series:
    regras = pd.read_csv(config.REF_DIR / "evg_sustentabilidade.csv", sep=";", dtype=str)
    casou = pd.Series(False, index=df.index)
    for r in regras.itertuples():
        casou |= df[r.campo].fillna("").str.contains(r.padrao, case=False, regex=True)
    return casou


def transform(regs: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(regs)
    if df.empty:
        return df
    # a mesma matricula pode vir em mais de um bimestre: vale a extracao mais recente
    # (nov-dez/2024 traz cada linha duas vezes); sem codigo, a linha inteira e a chave
    chave = df["cod_matricula"].fillna(df.drop(columns=["ano_arquivo", "bimestre"]).astype(str).agg("|".join, axis=1))
    df = df.assign(_chave=chave).sort_values(["ano_arquivo", "bimestre"])
    df = df.drop_duplicates("_chave", keep="last").drop(columns="_chave")
    dt = _data(df["dt_matricula"])
    df["data"] = dt.dt.strftime("%Y-%m-%d")
    df["periodo"] = dt.dt.strftime("%Y-%m")
    df["ano"] = dt.dt.year
    df["carga_horaria"] = pd.to_numeric(df["carga_horaria"], errors="coerce")
    df["concluida"] = df["sit_matricula"].map(_norm).str.startswith("CONCLU")
    df["sustentabilidade"] = _sustentavel(df)
    return df[df["periodo"].notna()].reset_index(drop=True)


def run(*, dry_run: bool = False, inicio: str | None = None, fim: str | None = None, offline: bool = False,
        **_: object) -> None:
    janela = Janela.de_args(inicio or "2023-01", fim)
    regs, info = extract(janela, offline=offline)
    report_counts("EVG - arquivos bimestrais", info)
    df = transform(regs)
    if df.empty:
        print("EVG: nenhuma matricula da UFPB na janela")
        return
    c = df[df["concluida"]]
    report_counts("EVG - matriculas UFPB por ano", df.groupby("ano").size().rename(str).to_dict())
    report_counts("EVG - certificacoes (concluidas) por ano", c.groupby("ano").size().rename(str).to_dict())
    report_counts("EVG - pessoas distintas certificadas por ano", c.groupby("ano")["pessoa"].nunique().rename(str).to_dict())
    report_counts("EVG - certificacoes em sustentabilidade por ano",
                  c[c["sustentabilidade"]].groupby("ano").size().rename(str).to_dict())
    if not dry_run:
        save_processed(df, COLLECTION)
    replace_by(COLLECTION, df, "periodo", dry_run=dry_run)


if __name__ == "__main__":
    run()
