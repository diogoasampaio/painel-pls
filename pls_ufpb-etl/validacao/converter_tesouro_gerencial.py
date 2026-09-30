"""Converte a exportacao CSV do Tesouro Gerencial nos arquivos de validacao
do ETL:
  data/validacao/tesouro_gerencial_liquidado.csv  ano;natureza;liquidado;pago
  data/validacao/tesouro_gerencial_mensal.csv     periodo;natureza;liquidado;pago
com pago = despesas pagas + restos a pagar pagos.

Relatorio esperado no TG (ver README, secao Validacao):
  linhas   Ano Lancamento | Natureza Despesa Detalhada | Mes Lancamento
  colunas  DESPESAS LIQUIDADAS | DESPESAS PAGAS | 06. Restos a Pagar Pagos (F)
  filtro   Orgao UGE = 26240 e os anos (sem UG Executora: com o mes nas
           linhas o TG recusa a consulta por "associacao cartesiana")

Formato que o TG exporta (visto em 2026-09): latin-1, separado por TAB,
linha de titulo e linha vazia antes do cabecalho, coluna do nome da
natureza sem cabecalho, valores "1.234,56" e celula vazia = zero. DESPESAS
PAGAS sai sem centavos -- irrelevante para a tolerancia da validacao.

Os valores mensais do TG sao ACUMULADOS no ano (verificado: proventos vao
de R$ 39 mi em JAN a R$ 500 mi em DEZ):
- liquidadas e pagas: saldo acumulado. Anual = ultimo periodo (014, o
  encerramento, nos anos fechados; o ultimo mes no ano corrente). Mes =
  diferenca para o periodo anterior.
- "06. Restos a Pagar Pagos (F)": acumulado DUAS vezes -- cada linha e a
  soma corrida de um saldo que ja e acumulado (na folha sobe exatamente o
  mesmo valor em todo periodo, inclusive 013 e 014, sem pagamento). Saldo
  real = diferenca entre periodos consecutivos; mes = segunda diferenca.
Sem o mes no relatorio o TG soma os saldos de todos os meses (~6,5x).

Uso:
    python validacao/converter_tesouro_gerencial.py "<exportacao do TG>.csv"
"""

from __future__ import annotations

import io
import re
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common import config  # noqa: E402
from common.text import norm  # noqa: E402

SAIDA = config.DATA_DIR / "validacao" / "tesouro_gerencial_liquidado.csv"
SAIDA_MENSAL = config.DATA_DIR / "validacao" / "tesouro_gerencial_mensal.csv"

MESES = {m: i for i, m in enumerate(["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"], 1)}


def _brl(v: str) -> float:
    """Sempre formato brasileiro: '3.677.037.587' e '1.234,56'. O parse_valor
    generico leria '3.677.037.587' como decimal."""
    v = v.strip()
    return float(v.replace(".", "").replace(",", ".")) if v else 0.0


def _mes(v: str) -> int | None:
    t = norm(v)
    for nome, n in MESES.items():
        if t.startswith(nome):
            return n
    d = re.match(r"\d+", t)
    # 013 e 014: periodos de encerramento do exercicio, depois de DEZ
    return int(d.group()) if d and 1 <= int(d.group()) <= 14 else None


def ler(origem: Path) -> pd.DataFrame:
    linhas = origem.read_text(encoding="latin-1").splitlines()
    inicio = next(i for i, l in enumerate(linhas) if "ano lan" in norm(l))
    df = pd.read_csv(io.StringIO("\n".join(linhas[inicio:])), sep="\t", dtype=str, keep_default_na=False)
    cols = {norm(c): c for c in df.columns}

    def col(trecho: str) -> str:
        achou = [orig for n, orig in cols.items() if trecho in n]
        if not achou:
            raise KeyError(f"coluna com '{trecho}' nao encontrada na exportacao: {list(df.columns)}")
        return achou[0]

    mes_col = next((orig for n, orig in cols.items() if n.startswith("mes")), None)
    if mes_col is None:
        raise SystemExit(
            "Exportacao sem 'Mes Lancamento' nas linhas: os valores do TG sao acumulados e sairiam inflados. "
            "Acrescente Mes Lancamento ao relatorio e exporte de novo."
        )
    out = pd.DataFrame({
        "ano": df[col("ano lan")].str.strip(),
        "natureza": df[col("natureza")].map(lambda v: re.sub(r"\D", "", v)),
        "mes": df[mes_col].map(_mes),
        "liquidadas": df[col("liquidadas")].map(_brl),
        "pagas": df[col("despesas pagas")].map(_brl),
        "rp": df[col("restos a pagar pagos")].map(_brl),
    })
    return out[(out["natureza"].str.len() == 8) & out["mes"].notna()]


def serie(out: pd.DataFrame) -> pd.DataFrame:
    """Saldos acumulados reais por (ano, natureza, mes), periodos 1..ultimo do
    ano. O TG omite linhas sem nenhum valor; ali o saldo repete o anterior
    (antes do primeiro movimento, zero).

    L, P  liquidado e pago acumulados
    C     restos a pagar pagos acumulados (desfeita a soma corrida)
    """
    partes = []
    ultimo_do_ano = out.groupby("ano")["mes"].max()
    for (ano, nat), g in out.groupby(["ano", "natureza"]):
        g = g.groupby("mes")[["liquidadas", "pagas", "rp"]].last()
        g = g.reindex(range(1, int(ultimo_do_ano[ano]) + 1)).ffill().fillna(0.0)
        partes.append(pd.DataFrame({
            "ano": ano, "natureza": nat, "mes": g.index,
            "L": g["liquidadas"].values, "P": g["pagas"].values,
            "C": g["rp"].diff().fillna(g["rp"]).values,
        }))
    return pd.concat(partes, ignore_index=True)


def anual(s: pd.DataFrame) -> pd.DataFrame:
    fim = s[s["mes"] == s.groupby("ano")["mes"].transform("max")]
    print("periodo usado por ano:", fim.groupby("ano")["mes"].first().to_dict())
    return pd.DataFrame({
        "ano": fim["ano"], "natureza": fim["natureza"],
        "liquidado": fim["L"], "pago": fim["P"] + fim["C"],
    }).reset_index(drop=True)


def mensal(s: pd.DataFrame) -> pd.DataFrame:
    """Fluxo de cada mes; 013/014 entram em dezembro."""
    s = s.sort_values(["ano", "natureza", "mes"]).copy()
    g = s.groupby(["ano", "natureza"])
    s["liquidado"] = g["L"].diff().fillna(s["L"])
    s["pago"] = g["P"].diff().fillna(s["P"]) + g["C"].diff().fillna(s["C"])
    s["mes"] = s["mes"].clip(upper=12)
    m = s.groupby(["ano", "mes", "natureza"], as_index=False)[["liquidado", "pago"]].sum()
    m = m[(m["liquidado"].abs() > 0.005) | (m["pago"].abs() > 0.005)]
    m["periodo"] = m["ano"] + "-" + m["mes"].astype(int).astype(str).str.zfill(2)
    return m[["periodo", "natureza", "liquidado", "pago"]].reset_index(drop=True)


def converter(origem: Path) -> pd.DataFrame:
    return anual(serie(ler(origem)))


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    s = serie(ler(Path(sys.argv[1])))
    a, m = anual(s), mensal(s)
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    fmt = lambda v: f"{v:.2f}".replace(".", ",")  # noqa: E731
    for df, destino in ((a, SAIDA), (m, SAIDA_MENSAL)):
        df.assign(liquidado=df["liquidado"].map(fmt), pago=df["pago"].map(fmt)).to_csv(destino, sep=";", index=False)
        print(f"{len(df)} linhas gravadas em {destino}")
    print(a.groupby("ano").agg(naturezas=("natureza", "size"), liquidado=("liquidado", "sum"), pago=("pago", "sum")).round(2).to_string())


if __name__ == "__main__":
    main()
