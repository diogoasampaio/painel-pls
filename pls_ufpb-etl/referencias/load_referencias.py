"""Carga das tabelas de referencia do PLS (ref/*.csv) para o Mongo.

- pls_eixos: os 6 eixos tematicos do PLS UFPB 2025-2029 (Portaria SEGES/ME
  8.678/2021, art. 7o).
- pls_temas: temas operacionais do painel (energia, agua...), cada um
  ligado a um eixo, com rotulo e ordem de exibicao -- a API e o frontend
  leem daqui, nao de constantes no codigo.
- pls_area_construida: area construida por campus/unidade (m2), denominador
  dos indicadores por m2.
- pls_catalogo_indicadores: os indicadores do plano (tabelas 16 a 24) e as
  ampliacoes do painel, com meta e rota de automacao (modulo `metas`).
- pls_mapeamento: natureza de despesa -> tema/subtema. Editar o CSV e
  rodar `python run.py referencias` + reprocessar `despesas` muda a
  classificacao sem tocar em codigo.
- pls_regras_texto: regras aplicadas as descricoes de itens de empenho.

Nao depende de periodo: substitui as colecoes inteiras.
"""

from __future__ import annotations

import pandas as pd

from common import config, pls_map
from metas import catalogo
from common.mongo import get_db
from common.records import to_mongo_records
from common.validation import report_counts

TABELAS = {
    "pls_eixos": "eixos_pls",
    "pls_temas": "temas_pls",
    "pls_mapeamento": "mapeamento_natureza_pls",
    "pls_regras_texto": "regras_texto_pls",
    "pls_catalogo_indicadores": "indicadores_pls",
    "pls_area_construida": "area_construida",
    # questoes em aberto para a Comissao do PLS, mostradas na descricao dos indicadores (painel e fichas)
    "pls_decisoes_comissao": "decisoes_comissao",
}


def run(*, dry_run: bool = False, **_: object) -> None:
    frames = {col: pls_map._read_ref(arq) for col, arq in TABELAS.items()}

    temas_validos = set(frames["pls_temas"]["tema_codigo"])
    for col in ("pls_mapeamento", "pls_regras_texto"):
        invalidos = set(frames[col]["tema_codigo"]) - temas_validos
        if invalidos:
            raise ValueError(f"{col}: tema_codigo sem cadastro em temas_pls.csv: {sorted(invalidos)}")
    frames["pls_temas"]["ordem"] = pd.to_numeric(frames["pls_temas"]["ordem"])
    frames["pls_area_construida"]["area_m2"] = pd.to_numeric(frames["pls_area_construida"]["area_m2"])
    eixos_validos = set(frames["pls_eixos"]["eixo_pls"])
    for col in ("pls_temas", "pls_catalogo_indicadores"):
        invalidos = set(frames[col]["eixo_pls"]) - eixos_validos
        if invalidos:
            raise ValueError(f"{col}: eixo_pls sem cadastro em eixos_pls.csv: {sorted(invalidos)}")
    catalogo.validar(frames["pls_catalogo_indicadores"])
    dec = frames["pls_decisoes_comissao"]
    nucleo = set(pls_map._read_ref("nucleo_pls")["codigo"])
    citados = set(dec["indicadores"].str.split("|").explode())
    fora = citados - set(frames["pls_catalogo_indicadores"]["id"]) - nucleo
    if fora:
        raise ValueError(f"decisoes_comissao.csv: indicadores inexistentes: {sorted(fora)}")
    if not set(dec["situacao"]) <= {"pendente", "decidida"}:
        raise ValueError("decisoes_comissao.csv: situacao deve ser pendente ou decidida")
    frames["pls_catalogo_indicadores"] = catalogo.tipar(frames["pls_catalogo_indicadores"])
    frames["pls_catalogo_indicadores"]["ordem"] = range(1, len(frames["pls_catalogo_indicadores"]) + 1)

    report_counts("referencias", {col: len(df) for col, df in frames.items()})
    conferir = frames["pls_mapeamento"].query("confianca == 'conferir'")["natureza"].tolist()
    if conferir:
        print(f"  atencao: naturezas marcadas para conferir na tabela vigente: {', '.join(conferir)}")

    if dry_run:
        print("[dry-run] colecoes de referencia nao gravadas")
        return
    if config.SO_ARQUIVOS:
        print("[so-arquivos] referencias ficam so em ref/*.csv")
        return
    db = get_db()
    for col, df in frames.items():
        db[col].delete_many({})
        db[col].insert_many(to_mongo_records(df))
        print(f"{len(df)} documentos gravados em '{col}'")


if __name__ == "__main__":
    run()
