"""Plano de acoes do PLS UFPB 2025-2029 x acompanhamento -> pls_acoes.

Plano: ref/acoes_pls_ufpb.csv -- as 61 acoes das Tabelas 16 a 24 do PLS (cada
uma com objetivo, meta, indicador, responsavel, prazos, recursos e riscos) e as
rotinas de governanca da secao 7 do PLS e das Portarias SEGES 8.678/2021 e
5.376/2023. Muda so com revisao do PLS.

Acompanhamento: data/metas/acompanhamento_acoes.csv, preenchido pelos
responsaveis a cada semestre (ciclo AAAA-S1 / AAAA-S2, como os relatorios
semestrais da secao 7.2 do PLS): situacao, % de execucao, evidencia (link ou
processo SIPAC), justificativa e as quatro perguntas da avaliacao do PLS
(avaliacao, facilitadores, dificuldades, ajuste sugerido). Se o arquivo nao
existe, e criado com uma linha em branco por acao para o ciclo atual.

Situacao calculada (contra o prazo e o hoje):
  entrega   concluida | em_andamento | nao_iniciada | atrasada (fim vencido e
            informada como nao concluida) | vencida_sem_informacao (fim vencido e
            ninguem informou) | a_iniciar (inicio no futuro) | sem_informacao
  continua  em_dia (realizada no ciclo ou verificada pelo painel) | pendente
            (nao realizada no ciclo) | a_iniciar | sem_informacao
  qualquer  suspensa | cancelada (informadas)

Verificacao pelo painel (coluna `verificacao`): `painel` = a propria coleta do
painel comprova a execucao (ex.: "monitorar o consumo de agua" com as faturas
lidas); `indicio` = ha dado relacionado (ex.: itens de LED empenhados), mas a
Comissao confirma. Regra `metrica:<metrica>[|<subtema>]` sobre pls_indicadores,
com dado nos ultimos 6 meses; `metrica:*` = qualquer dado recente.

N15 (nucleo): % das acoes exigiveis (inicio ja passou, nao canceladas) que
estao concluidas, em dia ou em andamento dentro do prazo.
"""

from __future__ import annotations

import re
from datetime import date

import pandas as pd

from common import config
from common.mongo import get_db
from common.records import to_mongo_records
from common.storage import load_processed, save_processed
from common.validation import report_counts

COLLECTION = "pls_acoes"
TIPOS = {"entrega", "continua"}
VERIFICACAO = {"informada", "indicio", "painel"}
SITUACOES = {"nao_iniciada", "em_andamento", "concluida", "realizada_no_ciclo", "nao_realizada_no_ciclo",
             "suspensa", "cancelada"}
COLUNAS_ACOMP = ["acao_id", "ciclo", "situacao", "percentual", "evidencia", "justificativa", "facilitadores",
                 "dificuldades", "ajuste_sugerido", "informado_por", "data_registro"]
EXIGE_EVIDENCIA = {"concluida", "realizada_no_ciclo"}
NO_PRAZO = {"concluida", "em_dia", "em_andamento"}
MESES_RECENTES = 6


def arquivo_acompanhamento():
    return config.DATA_DIR / "metas" / "acompanhamento_acoes.csv"


def ciclo_de(d: date) -> str:
    return f"{d.year}-S{1 if d.month <= 6 else 2}"


def plano() -> pd.DataFrame:
    df = pd.read_csv(config.REF_DIR / "acoes_pls_ufpb.csv", sep=";", dtype=str, keep_default_na=False)
    erros = []
    if not df["id"].is_unique:
        erros.append(f"ids repetidos: {df.loc[df['id'].duplicated(), 'id'].tolist()}")
    for col, validos in (("tipo", TIPOS), ("verificacao", VERIFICACAO)):
        ruins = sorted(set(df[col]) - validos)
        if ruins:
            erros.append(f"{col} invalido: {ruins}")
    for col in ("inicio", "fim"):
        ruins = df.loc[~df[col].str.fullmatch(r"\d{4}-\d{2}"), "id"].tolist()
        if ruins:
            erros.append(f"{col} fora de AAAA-MM: {ruins}")
    sem_regra = df.loc[(df["verificacao"] != "informada") & ~df["regra_verificacao"].str.startswith("metrica:"), "id"].tolist()
    if sem_regra:
        erros.append(f"verificacao automatica sem regra metrica:: {sem_regra}")
    if erros:
        raise ValueError("ref/acoes_pls_ufpb.csv: " + "; ".join(erros))
    return df


def modelo_ciclo(acoes: pd.DataFrame, ciclo: str) -> pd.DataFrame:
    """Uma linha em branco por acao para o responsavel preencher."""
    df = pd.DataFrame({"acao_id": acoes["id"], "ciclo": ciclo})
    for c in COLUNAS_ACOMP[2:]:
        df[c] = ""
    return df[COLUNAS_ACOMP]


def acompanhamento(acoes: pd.DataFrame, hoje: date) -> pd.DataFrame:
    arq = arquivo_acompanhamento()
    if not arq.exists():
        arq.parent.mkdir(parents=True, exist_ok=True)
        modelo_ciclo(acoes, ciclo_de(hoje)).to_csv(arq, sep=";", index=False, encoding="utf-8")
        print(f"  criado {arq} com uma linha por acao para o ciclo {ciclo_de(hoje)}")
    df = pd.read_csv(arq, sep=";", dtype=str, keep_default_na=False)
    faltando = set(COLUNAS_ACOMP) - set(df.columns)
    if faltando:
        raise ValueError(f"{arq}: colunas ausentes {sorted(faltando)}")
    erros = []
    desconhecidas = sorted(set(df["acao_id"]) - set(acoes["id"]))
    if desconhecidas:
        erros.append(f"acao_id fora do plano: {desconhecidas}")
    ruins = sorted(set(df["situacao"]) - SITUACOES - {""})
    if ruins:
        erros.append(f"situacao invalida: {ruins} (validas: {', '.join(sorted(SITUACOES))})")
    ciclos = df.loc[~df["ciclo"].str.fullmatch(r"\d{4}-S[12]"), "ciclo"].unique().tolist()
    if ciclos:
        erros.append(f"ciclo fora de AAAA-S1/AAAA-S2: {ciclos}")
    if erros:
        raise ValueError(f"{arq}: " + "; ".join(erros))
    return df[df["situacao"] != ""]


def _verificacao_painel(regra: str, ind: pd.DataFrame, hoje: date) -> tuple[bool, str]:
    m = re.fullmatch(r"metrica:([^|]+)(?:\|(.+))?", regra or "")
    if not m or ind.empty:
        return False, ""
    metrica, subtema = m.groups()
    sel = ind if metrica == "*" else ind[ind["metrica"] == metrica]
    if subtema:
        sel = sel[sel["subtema"] == subtema]
    sel = sel[sel["valor_nominal"].fillna(0) > 0]
    if sel.empty:
        return False, "sem dado no painel"
    ultimo = sel["periodo"].max()
    a, mes = map(int, ultimo.split("-"))
    recente = (hoje.year - a) * 12 + (hoje.month - mes) <= MESES_RECENTES
    alvo = "dados do painel" if metrica == "*" else metrica + (f" ({subtema})" if subtema else "")
    return recente, f"{alvo}: último mês com dado {ultimo[5:]}/{ultimo[:4]}"


def _situacao(a: pd.Series, info: pd.Series | None, verificada: bool, hoje: date) -> str:
    informada = info["situacao"] if info is not None else ""
    if informada in {"suspensa", "cancelada"}:
        return informada
    mes_atual = f"{hoje:%Y-%m}"
    if a["inicio"] > mes_atual:
        return "a_iniciar"
    if a["tipo"] == "continua":
        if informada == "realizada_no_ciclo" or (verificada and a["verificacao"] == "painel"):
            return "em_dia"
        if informada == "nao_realizada_no_ciclo":
            return "pendente"
        return "sem_informacao"
    if informada == "concluida":
        return "concluida"
    if a["fim"] < mes_atual:
        # sem informacao nao e o mesmo que atraso: pode ter sido feita e nao informada
        return "atrasada" if informada else "vencida_sem_informacao"
    return informada or "sem_informacao"


def build(hoje: date | None = None) -> tuple[pd.DataFrame, dict]:
    hoje = hoje or date.today()
    acoes = plano()
    acomp = acompanhamento(acoes, hoje)
    ultimo = acomp.sort_values(["ciclo", "data_registro"]).drop_duplicates("acao_id", keep="last").set_index("acao_id")
    ind = load_processed("pls_indicadores")
    linhas = []
    for _, a in acoes.iterrows():
        info = ultimo.loc[a["id"]] if a["id"] in ultimo.index else None
        verificada, evid_painel = (False, "")
        if a["verificacao"] != "informada":
            verificada, evid_painel = _verificacao_painel(a["regra_verificacao"], ind, hoje)
        sit = _situacao(a, info, verificada, hoje)
        get = (lambda c: info[c] if info is not None else "")  # noqa: E731
        linhas.append({
            **a.to_dict(),
            "situacao_informada": get("situacao"), "ciclo_informado": get("ciclo"),
            "percentual": pd.to_numeric(get("percentual"), errors="coerce"),
            "evidencia": get("evidencia"), "justificativa": get("justificativa"),
            "informado_por": get("informado_por"), "data_registro": get("data_registro"),
            "verificada_painel": verificada, "evidencia_painel": evid_painel,
            "situacao": sit,
            "sem_evidencia": get("situacao") in EXIGE_EVIDENCIA and not get("evidencia"),
            "exigivel": sit not in {"a_iniciar", "cancelada"},
        })
    df = pd.DataFrame(linhas)
    exig = df[df["exigivel"]]
    no_prazo = exig["situacao"].isin(NO_PRAZO) & ~exig["sem_evidencia"]
    resumo = {
        "acoes": len(df), "exigiveis": len(exig),
        "no_prazo": int(no_prazo.sum()),
        "atrasadas": int((exig["situacao"] == "atrasada").sum()),
        "vencidas_sem_informacao": int((exig["situacao"] == "vencida_sem_informacao").sum()),
        "sem_informacao": int((exig["situacao"] == "sem_informacao").sum()),
        "verificadas_painel": int(df["verificada_painel"].sum()),
        "indice_cumprimento": round(100 * no_prazo.mean(), 1) if len(exig) else None,
        "data_referencia": hoje.isoformat(),
    }
    return df, resumo


def run(*, dry_run: bool = False, **_: object) -> None:
    df, resumo = build()
    report_counts("acoes do PLS por situacao", df["situacao"].value_counts().to_dict())
    report_counts("acoes do PLS - resumo", {k: v for k, v in resumo.items() if k != "data_referencia"})
    sem_ev = df.loc[df["sem_evidencia"], "id"].tolist()
    if sem_ev:
        print(f"  atencao: concluida/realizada sem evidencia (nao conta no indice): {sem_ev}")
    if dry_run:
        print(f"[dry-run] {len(df)} documentos seriam gravados em '{COLLECTION}'")
        return
    save_processed(df.assign(indice_cumprimento=resumo["indice_cumprimento"], data_referencia=resumo["data_referencia"]),
                   COLLECTION)
    if config.SO_ARQUIVOS:
        print(f"[so-arquivos] {len(df)} documentos de '{COLLECTION}' so em data/processed")
        return
    db = get_db()
    db[COLLECTION].delete_many({})
    db[COLLECTION].insert_many(to_mongo_records(df))
    print(f"{len(df)} documentos gravados em '{COLLECTION}'")


if __name__ == "__main__":
    run()
