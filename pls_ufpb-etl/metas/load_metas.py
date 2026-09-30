"""Valor anual de cada indicador do PLS e situacao frente a meta -> pls_metas.

Origem do valor, conforme o catalogo (ref/indicadores_pls.csv):
  automatico   calculado aqui a partir de pls_indicadores (parquet)
  lancado      data/metas/valores_informados.csv -- cobre os indicadores
               `informado` e os de `integracao` enquanto a integracao nao
               existe. Uma integracao nova grava neste mesmo formato (ou
               vira um `calculo` no catalogo) e o resto nao muda.
Um valor lancado para indicador automatico prevalece (ex.: consumo real de
copos vindo do almoxarifado no lugar da compra) e o relatorio avisa.

valores_informados.csv (modelo em ref/modelo_valores_informados.csv):
  indicador_id;ano;valor;fonte;informado_por;data_registro;observacao
`valor` na unidade do catalogo, formato brasileiro (1.234,5); para calculo=per_capita, o total (ex.: m³
do ano), que o ETL divide pela comunidade academica (common/comunidade.py).

situacao: atingida | nao_atingida | em_andamento (ano corrente ou sem
referencia para comparar) | linha_de_base (o proprio ano_base) |
historico (ano anterior a linha de base) |
acompanhamento (sem meta).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from common import comunidade as comunidade_ufpb
from common import config
from common.mongo import get_db
from common.records import to_mongo_records
from common.storage import load_processed, save_processed
from common.validation import report_counts
from metas import catalogo

COLLECTION = "pls_metas"
COLUNAS_LANCADOS = ["indicador_id", "ano", "valor", "fonte", "informado_por", "data_registro", "observacao"]


def arquivo_lancados():
    return config.DATA_DIR / "metas" / "valores_informados.csv"


def _lancados(ids_validos: set[str]) -> pd.DataFrame:
    arq = arquivo_lancados()
    if not arq.exists():
        return pd.DataFrame(columns=COLUNAS_LANCADOS)
    df = pd.read_csv(arq, sep=";", dtype=str, keep_default_na=False)
    faltando = set(COLUNAS_LANCADOS) - set(df.columns)
    if faltando:
        raise ValueError(f"{arq}: colunas ausentes {sorted(faltando)}")
    desconhecidos = sorted(set(df["indicador_id"]) - ids_validos)
    if desconhecidos:
        raise ValueError(f"{arq}: indicador_id fora do catalogo: {desconhecidos}")
    df["ano"] = pd.to_numeric(df["ano"], errors="raise").astype(int)
    df["valor"] = pd.to_numeric(df["valor"].str.replace(".", "", regex=False).str.replace(",", ".", regex=False), errors="raise")
    dup = df[df.duplicated(["indicador_id", "ano"], keep=False)]
    if not dup.empty:
        raise ValueError(f"{arq}: mais de um valor para {dup[['indicador_id', 'ano']].drop_duplicates().values.tolist()}")
    return df[COLUNAS_LANCADOS]


# metricas de eventos (contratacoes publicadas): mes sem evento nao e mes sem dado
POR_EVENTO = ("contratacoes_pncp", "contratacoes_pncp_valor", "editais_marcadores", "compras_compartilhadas")


def _automatico(calc: dict, ind: pd.DataFrame) -> pd.Series:
    if ind.empty:
        return pd.Series(dtype=float)
    m = ind["metrica"] == calc["metrica"]
    if calc["tema"]:
        m &= ind["tema_codigo"] == calc["tema"]
    base = m.copy()  # denominador da razao: mesma metrica, sem o filtro de subtema
    if calc["subtemas"]:
        m &= ind["subtema"].isin(calc["subtemas"])
    if calc["campo"] == "valor_por_m2":
        # razao das somas, nao soma das razoes: kWh da UFPB / area dos campi que
        # entram na soma (subtema 'Campus X' tem a area do campus; os demais, a
        # da UFPB inteira -- a mesma em todos, conta uma vez so)
        sel = ind[m]
        area = sel.drop_duplicates(["ano", "area_m2"]).groupby("ano")["area_m2"].sum()
        num = sel.groupby("ano")["valor_real"].sum() / area
    else:
        num = ind[m].groupby("ano")[calc["campo"]].sum()
    # valor em R$ corrigido pelo IPCA: guarda o nominal (mesma conta sem deflator) para conferencia
    sel = ind[m]
    if calc["campo"] != "valor_nominal" and "ref_ipca" in sel and sel["ref_ipca"].notna().any():
        nominal = sel["valor_nominal"]
        if calc["campo"] == "valor_real_per_capita":
            nominal = nominal / sel["comunidade"]
        nom = nominal.groupby(sel["ano"]).sum()
        if calc["campo"] == "valor_por_m2":
            nom = nom / area
        num.attrs["nominal"] = nom.to_dict()
        num.attrs["ref_ipca"] = str(sel["ref_ipca"].dropna().max())
    # ano completo = meses carregados da FONTE (a metrica em qualquer subtema):
    # compra esporadica (copos, LED) nao tem valor todo mes e o ano nunca fecharia.
    # Itens de empenho: mes sem item que case regra de texto nao e mes faltando;
    # vale a cobertura das despesas (mesmos arquivos diarios)
    # Contratacoes (PNCP/Compras.gov.br): mes sem contratacao publicada tambem nao e mes faltando --
    # a lista do ano sai inteira da API; vale a mesma cobertura das despesas
    if calc["metrica"] in ("empenhado_itens", "quantidade_itens", "pago_acao", "empenhado_material_consumo",
                           "adesao_avn_pct", *POR_EVENTO):
        fonte = ind["metrica"] == "pago"
    elif calc["metrica"].startswith("evg_"):
        fonte = ind["metrica"] == "evg_matriculas"  # cobertura = meses com matricula no arquivo da ENAP
    else:
        fonte = base
    num.attrs["meses"] = ind[fonte].groupby("ano")["mes"].nunique().to_dict()
    if not calc.get("razao_subtemas"):
        return num
    d = ind[base & ind["subtema"].isin(calc["razao_subtemas"])]
    den = d.groupby("ano")[calc["campo"]].sum()
    out = (100 * num.reindex(den.index, fill_value=0) / den).dropna()
    out.attrs["meses"] = (num.attrs["meses"] if calc["metrica"] in POR_EVENTO
                          else d.groupby("ano")["mes"].nunique().to_dict())
    return out


def _por_pessoa(total: float, ano: int, comunidade: pd.Series) -> float:
    disponiveis = comunidade[comunidade.index <= ano]
    return total / disponiveis.iloc[-1] if len(disponiveis) else np.nan


def _situacao(r: dict, serie: dict[int, float], completos: dict[int, bool]) -> tuple[float | None, int | None, str]:
    """(variacao_pct, ano_referencia, situacao) de um ano de um indicador.
    Ano incompleto nunca reprova; comparacao com ano de referencia incompleto
    (ex.: 2023 so com dezembro) fica em_andamento."""
    completo = completos.get(r["ano"], True)
    tipo, meta = r["tipo_meta"], r["meta_valor"]
    if tipo == "acompanhamento":
        return None, None, "acompanhamento"
    valor = serie[r["ano"]]
    ref_ano = None
    variacao = None
    if tipo in catalogo.VARIACAO:
        if r["ano_base"] is not None and r["ano_base"] == r["ano_base"] and r["ano"] < int(r["ano_base"]):
            return None, int(r["ano_base"]), "historico"  # antes da linha de base do plano
        ref_ano = int(r["ano_base"]) if tipo.endswith("_vs_base") else r["ano"] - 1
        base = serie.get(ref_ano)
        tem_base = r["ano_base"] is not None and r["ano_base"] == r["ano_base"]
        if ref_ano == r["ano"] or (tem_base and r["ano"] == int(r["ano_base"])):
            # reducao_anual: o ano-base do plano tambem e so linha de base
            return None, ref_ano, "linha_de_base"
        if ref_ano > r["ano"]:
            return None, ref_ano, "historico"  # antes da linha de base do plano
        if base is None or base == 0:
            return None, ref_ano, "em_andamento"
        variacao = (valor / base - 1) * 100
        if not completo or not completos.get(ref_ano, True):
            # soma de ano parcial nao se compara com ano cheio (em nenhum dos lados)
            return None, ref_ano, "em_andamento"
        ok = variacao <= -meta if tipo.startswith("reducao") else variacao >= meta
    elif tipo == "booleano":
        ok = valor >= 1
    elif tipo == "maximo":
        ok = valor <= meta
    else:
        ok = valor >= meta
    if not completo and not ok:
        return variacao, ref_ano, "em_andamento"
    return variacao, ref_ano, "atingida" if ok else "nao_atingida"


def faixas() -> pd.DataFrame:
    """ref/faixas_execucao.csv: faixas numericas (alcance_minimo) e as categorias sem alcance."""
    df = pd.read_csv(config.REF_DIR / "faixas_execucao.csv", sep=";", dtype={"codigo": str, "faixa": str})
    return df.sort_values("ordem")


def alcance(tipo: str, meta, valor, variacao, situacao: str) -> float | None:
    """Grau de alcance da meta no ano, de 0 a 100. So existe quando a situacao foi
    avaliada (atingida/nao_atingida); piora em relacao a referencia vale 0.

      minimo   valor / meta            maximo   meta / valor (100 se valor <= meta)
      reducao  reducao obtida / meta   aumento  aumento obtido / meta
      booleano 100 ou 0
    """
    if situacao not in ("atingida", "nao_atingida"):
        return None
    if situacao == "atingida":
        return 100.0
    if tipo == "booleano":
        return 0.0
    if tipo in catalogo.VARIACAO:
        if variacao is None or not meta:
            return None
        obtido = -variacao if tipo.startswith("reducao") else variacao
        a = 100 * obtido / meta
    elif tipo == "maximo":
        a = 100 * meta / valor if valor else None
    else:
        a = 100 * valor / meta if meta else None
    return None if a is None else round(min(max(a, 0.0), 100.0), 1)


def faixa_de(alcance_pct: float | None, tipo: str, situacao: str | None, tab: pd.DataFrame | None = None) -> str:
    tab = faixas() if tab is None else tab
    if tipo == "acompanhamento":
        return "sem_meta"
    if situacao is None:
        return "sem_dado"
    if alcance_pct is None:
        return "nao_avaliavel"
    numericas = tab.dropna(subset=["alcance_minimo"]).sort_values("alcance_minimo", ascending=False)
    return next(r.codigo for r in numericas.itertuples() if alcance_pct >= r.alcance_minimo)


def build() -> pd.DataFrame:
    cat = catalogo.carregar()
    lanc = _lancados(set(cat["id"]))
    ind = load_processed("pls_indicadores")
    comunidade = comunidade_ufpb.ufpb()["comunidade"]

    tab_faixas = faixas()
    linhas = []
    for r in cat.itertuples():
        calc = catalogo.parse_calculo(r.calculo)
        valores: dict[int, dict] = {}
        meses: dict[int, int] = {}
        if calc and calc["tipo"] == "ind":
            auto = _automatico(calc, ind)
            meses = auto.attrs.get("meses", {})
            nominal = auto.attrs.get("nominal", {})
            for ano, v in auto.items():
                valores[int(ano)] = {"valor": float(v), "origem": "automatico", "fonte": "Portal da Transparência (ETL)"}
                if ano in nominal:
                    valores[int(ano)].update(valor_nominal=float(nominal[ano]), ref_ipca=auto.attrs["ref_ipca"])
        for l in lanc[lanc["indicador_id"] == r.id].itertuples():
            if l.ano in valores:
                print(f"  {r.id} {l.ano}: valor lancado substitui o automatico")
            v = float(l.valor)
            origem = "lancado"
            if calc and calc["tipo"] == "per_capita":
                v = _por_pessoa(v, l.ano, comunidade)
                origem = "lancado+comunidade"
            valores[l.ano] = {
                "valor": v, "origem": origem, "fonte": l.fonte,
                "informado_por": l.informado_por, "data_registro": l.data_registro, "observacao": l.observacao,
            }
        serie = {a: d["valor"] for a, d in valores.items() if d["valor"] == d["valor"]}
        # lancamento manual e anual (fechado); automatico so com os 12 meses com dado
        completos = {a: d["origem"] != "automatico" or meses.get(a, 0) == 12 for a, d in valores.items()}
        for ano, d in sorted(valores.items()):
            completo = completos[ano]
            base = {"ano": ano, "tipo_meta": r.tipo_meta, "meta_valor": r.meta_valor, "ano_base": r.ano_base}
            var, ref_ano, sit = _situacao(base, serie, completos) if ano in serie else (None, None, "em_andamento")
            alc = alcance(r.tipo_meta, r.meta_valor, serie.get(ano), var, sit)
            linhas.append({
                "alcance_pct": alc, "faixa": faixa_de(alc, r.tipo_meta, sit, tab_faixas),
                "indicador_id": r.id, "eixo_pls": r.eixo_pls, "ano": ano, "unidade": r.unidade,
                "ano_completo": completo, "meta_valor": r.meta_valor, "tipo_meta": r.tipo_meta,
                "ano_referencia": ref_ano, "variacao_pct": var, "situacao": sit, **d,
            })
    cols = ["indicador_id", "eixo_pls", "ano", "valor", "valor_nominal", "ref_ipca", "unidade", "origem", "fonte", "informado_por", "data_registro",
            "observacao", "ano_completo", "tipo_meta", "meta_valor", "ano_referencia", "variacao_pct", "situacao",
            "alcance_pct", "faixa"]
    return pd.DataFrame(linhas, columns=cols)


def run(*, dry_run: bool = False, **_: object) -> None:
    df = build()
    cat = catalogo.carregar()
    report_counts("indicadores do catalogo por automacao", cat.groupby("automacao").size().to_dict())
    report_counts("valores anuais por origem", df.groupby("origem").size().to_dict() if not df.empty else {})
    sem_valor = sorted(set(cat.loc[cat["tipo_meta"] != "acompanhamento", "id"]) - set(df["indicador_id"]))
    if sem_valor:
        print(f"  {len(sem_valor)} indicadores do plano ainda sem valor (lancar em {arquivo_lancados()})")
    if dry_run:
        print(f"[dry-run] {len(df)} documentos seriam gravados em '{COLLECTION}'")
        return
    save_processed(df, COLLECTION)
    if config.SO_ARQUIVOS:
        print(f"[so-arquivos] {len(df)} documentos de '{COLLECTION}' so em data/processed")
        return
    # colecao pequena: substitui inteira (indicador ou lancamento removido some)
    db = get_db()
    db[COLLECTION].delete_many({})
    if len(df):
        db[COLLECTION].insert_many(to_mongo_records(df))
    print(f"{len(df)} documentos gravados em '{COLLECTION}'")


if __name__ == "__main__":
    run()
