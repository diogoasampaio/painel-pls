"""Formularios do painel -> CSVs lidos por `acoes` e `metas`.

Os setores preenchem no proprio painel (pagina /pls/formularios) o
acompanhamento semestral das acoes do PLS e os valores dos indicadores
informados. A API grava cada envio, sem apagar nada, em:

  pls_form_acompanhamento  1 doc por envio: acao_id, ciclo, situacao, percentual,
                           evidencia, justificativa, facilitadores, dificuldades,
                           ajuste_sugerido, informado_por, setor, registrado_em
  pls_form_valores         1 doc por envio: indicador_id, ano, valor, fonte,
                           observacao, informado_por, setor, registrado_em

Este modulo (`python run.py formularios`, antes de metas e acoes) pega o
envio mais recente de cada (acao_id, ciclo) e de cada (indicador_id, ano) e
atualiza data/metas/acompanhamento_acoes.csv e valores_informados.csv. Os
CSVs continuam valendo: linha lancada direto no arquivo so e substituida
quando chega um envio do formulario mais novo para a mesma chave. O
historico completo fica no Mongo (auditoria).

Acesso (pls_form_acessos): cada setor recebe um token, guardado so como
hash SHA-256. O token vale para as acoes e os indicadores cujo
`responsavel` casa com a expressao do acesso ("*" = Comissao, tudo):

  python -m formularios.formularios criar "SINFRA" --responsavel "SINFRA"
  python -m formularios.formularios listar
  python -m formularios.formularios revogar "SINFRA"
"""

from __future__ import annotations

import argparse
import hashlib
import secrets
from datetime import datetime

import pandas as pd

from acoes.load_acoes import COLUNAS_ACOMP, arquivo_acompanhamento
from common import config
from metas.load_metas import COLUNAS_LANCADOS, arquivo_lancados

COL_ACOMP = "pls_form_acompanhamento"
COL_VALORES = "pls_form_valores"
COL_ACESSOS = "pls_form_acessos"


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _valor_br(v) -> str:
    if v is None or pd.isna(v):
        return ""
    return f"{float(v):.6f}".rstrip("0").rstrip(".").replace(".", ",")


def mesclar(csv: pd.DataFrame, envios: pd.DataFrame, chave: list[str], colunas: list[str]) -> tuple[pd.DataFrame, int]:
    """Envio mais recente de cada chave substitui a linha do CSV."""
    if envios.empty:
        return csv, 0
    envios = envios.sort_values("registrado_em").drop_duplicates(chave, keep="last")
    envios = envios.assign(data_registro=envios["registrado_em"].str[:10])[colunas].astype(str)
    csv = csv.astype(str)
    fica = ~csv.set_index(chave).index.isin(envios.set_index(chave).index)
    return pd.concat([csv[fica], envios], ignore_index=True).sort_values(chave).reset_index(drop=True), len(envios)


def _envios(db, colecao: str) -> pd.DataFrame:
    return pd.DataFrame(list(db[colecao].find({}, {"_id": 0})))


def run(*, dry_run: bool = False, **_: object) -> None:
    if config.SO_ARQUIVOS or not config.MONGO_URI:
        print("Formularios: sem Mongo (--so-arquivos ou MONGO_URI vazia); CSVs ficam como estao")
        return
    from common.mongo import get_db
    db = get_db()

    arq = arquivo_acompanhamento()
    csv = pd.read_csv(arq, sep=";", dtype=str, keep_default_na=False) if arq.exists() else pd.DataFrame(columns=COLUNAS_ACOMP)
    env = _envios(db, COL_ACOMP)
    if not env.empty:
        env["percentual"] = env["percentual"].map(_valor_br)
        env = env.fillna("")
    novo, n = mesclar(csv, env, ["acao_id", "ciclo"], COLUNAS_ACOMP)
    print(f"Formularios: {n} acompanhamento(s) de acao vindos do painel")
    if n and not dry_run:
        novo.to_csv(arq, sep=";", index=False, encoding="utf-8")

    arq = arquivo_lancados()
    csv = pd.read_csv(arq, sep=";", dtype=str, keep_default_na=False) if arq.exists() else pd.DataFrame(columns=COLUNAS_LANCADOS)
    env = _envios(db, COL_VALORES)
    if not env.empty:
        env["valor"] = env["valor"].map(_valor_br)
        env["ano"] = env["ano"].astype(int).astype(str)
        env = env.fillna("")
    novo, n = mesclar(csv, env, ["indicador_id", "ano"], COLUNAS_LANCADOS)
    print(f"Formularios: {n} valor(es) informado(s) vindos do painel")
    if n and not dry_run:
        arq.parent.mkdir(parents=True, exist_ok=True)
        novo.to_csv(arq, sep=";", index=False, encoding="utf-8")


# ---------------------------------------------------------------- acessos (CLI)

def main() -> None:
    from common.mongo import get_db
    p = argparse.ArgumentParser(description="Acessos dos setores aos formularios do painel")
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("criar", help="cria (ou troca) o token de um setor e mostra uma unica vez")
    c.add_argument("setor")
    c.add_argument("--responsavel", required=True,
                   help='expressao regular casada com a coluna responsavel das acoes e indicadores ("*" = todos)')
    sub.add_parser("listar")
    r = sub.add_parser("revogar")
    r.add_argument("setor")
    a = p.parse_args()
    col = get_db()[COL_ACESSOS]
    if a.cmd == "criar":
        token = secrets.token_urlsafe(24)
        col.update_one({"setor": a.setor}, {"$set": {
            "setor": a.setor, "hash": hash_token(token), "responsavel": a.responsavel, "ativo": True,
            "criado_em": datetime.now().isoformat(timespec="seconds")}}, upsert=True)
        print(f"Token de {a.setor} (guarde agora; so o hash fica no banco):\n\n  {token}\n")
    elif a.cmd == "listar":
        for d in col.find({}, {"_id": 0, "hash": 0}).sort("setor", 1):
            print(f"{d['setor']:<30} responsavel~/{d['responsavel']}/  {'ativo' if d.get('ativo') else 'revogado'}  {d.get('criado_em', '')}")
    else:
        res = col.update_one({"setor": a.setor}, {"$set": {"ativo": False}})
        print("revogado" if res.matched_count else f"setor {a.setor} nao encontrado")


if __name__ == "__main__":
    main()
