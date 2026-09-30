"""Fator de emissao de CO2 da energia eletrica do SIN (MCTI) -> pls_fator_sin.

Fonte: pagina "Fatores de emissao" do SIRENE/MCTI, secao "Fator medio -
Inventarios corporativos". A planilha "Inventarios Corporativos - <ano>"
traz o historico inteiro: fator medio mensal (tCO2/MWh) de 2006 ate o
ultimo mes publicado e o fator medio anual dos anos fechados. O nome do
arquivo muda a cada atualizacao (Inventario_2026_janago.xlsx), entao o link
e procurado na pagina a cada carga; a planilha e guardada em data/raw/mcti/
pelo nome (arquivo ja baixado nao e baixado de novo).

Layout: um bloco de 4 linhas por ano -- titulo; ano na coluna A e
"ANO - aaaa" na O; nomes dos meses em C..N e o fator anual na O; fatores
mensais em C..N (vazio nos meses ainda nao publicados).

Uso (indicadores._gee): kWh do mes x fator do MES, como na ferramenta do
Programa Brasileiro GHG Protocol. Mes ainda sem fator publicado usa o fator
anual do ultimo ano fechado e fica marcado como provisorio.

pls_fator_sin  1 linha por mes: periodo, ano, mes, fator_t_mwh (mensal),
               fator_anual_t_mwh (do ano, vazio no ano em curso), arquivo.
"""

from __future__ import annotations

import re
import time
from datetime import date

import pandas as pd

from common.http import USER_AGENT
from common.mongo import replace_by
from common.storage import raw_path, save_processed
from common.validation import report_counts

COLLECTION = "pls_fator_sin"
PAGINA = "https://www.gov.br/mcti/pt-br/acompanhe-o-mcti/sirene/dados-e-ferramentas/fatores-de-emissao"
_LINK = re.compile(r'href="([^"]*/arquivo/Inventario[^"]*\.xlsx)"', re.I)


def link_planilha(html: str) -> str:
    """URL da planilha de inventarios corporativos na pagina do MCTI."""
    achados = _LINK.findall(html)
    if not achados:
        raise RuntimeError("planilha 'Inventarios Corporativos' nao encontrada na pagina do MCTI (layout mudou?)")
    url = achados[0]
    return url if url.startswith("http") else "https://www.gov.br" + url


def _get(url: str):
    """GET com conexao nova a cada pedido: o gov.br derruba (reset) a segunda
    requisicao numa conexao reaproveitada e as vezes a primeira tambem."""
    import requests

    for tentativa in range(3):
        try:
            r = requests.get(url, headers={"User-Agent": USER_AGENT, "Connection": "close"}, timeout=120)
            r.raise_for_status()
            return r
        except requests.ConnectionError:
            if tentativa == 2:
                raise
            time.sleep(10)


def baixar() -> tuple[bytes, str]:
    url = link_planilha(_get(PAGINA).text)
    nome = url.rsplit("/", 1)[-1]
    arq = raw_path("mcti", nome)
    if not arq.exists():
        x = _get(url)
        if x.content[:2] != b"PK":
            raise RuntimeError(f"{url} nao devolveu uma planilha xlsx")
        arq.write_bytes(x.content)
    return arq.read_bytes(), nome


def ler(conteudo: bytes, arquivo: str = "") -> pd.DataFrame:
    import io

    import openpyxl

    ws = openpyxl.load_workbook(io.BytesIO(conteudo), data_only=True, read_only=True).worksheets[0]
    linhas = [list(r) for r in ws.iter_rows(values_only=True)]
    out = []
    for i, lin in enumerate(linhas):
        ano = lin[0] if lin else None
        if not (isinstance(ano, int) and 2000 <= ano <= 2100 and i + 2 < len(linhas)):
            continue
        meses, valores = linhas[i + 1], linhas[i + 2]
        if not (isinstance(meses[2], str) and meses[2].strip().lower().startswith("jan")):
            raise RuntimeError(f"bloco de {ano} fora do layout esperado (meses em C..N)")
        anual = meses[14] if len(meses) > 14 and isinstance(meses[14], (int, float)) else None
        for m in range(12):
            v = valores[2 + m]
            if isinstance(v, (int, float)):
                out.append({"periodo": f"{ano}-{m + 1:02d}", "ano": ano, "mes": m + 1, "fator_t_mwh": float(v),
                            "fator_anual_t_mwh": float(anual) if anual is not None else None, "arquivo": arquivo})
    df = pd.DataFrame(out)
    if df.empty:
        raise RuntimeError("nenhum fator mensal lido da planilha do MCTI")
    if not df["fator_t_mwh"].between(0, 1).all():
        raise RuntimeError("fator fora de 0 a 1 tCO2/MWh: unidade da planilha mudou?")
    return df


def run(*, dry_run: bool = False, **_: object) -> None:
    conteudo, nome = baixar()
    df = ler(conteudo, nome).assign(data_referencia=date.today().isoformat())
    ult = df.iloc[-1]
    print(f"  planilha {nome}: fatores mensais de {df['periodo'].iloc[0]} a {ult['periodo']}")
    report_counts("fator do SIN (MCTI)", {"meses": len(df), f"fator {ult['periodo']} (tCO2/MWh)": ult["fator_t_mwh"]})
    if not dry_run:
        save_processed(df, COLLECTION)
    replace_by(COLLECTION, df, "periodo", dry_run=dry_run)


if __name__ == "__main__":
    run()
