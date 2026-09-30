"""Viagens a servico da UFPB (Portal da Transparencia, download anual em
CSV) -> colecoes pls_viagens e pls_trechos.

Por que o CSV e nao a API: o endpoint /viagens nao traz os trechos
(origem/destino/meio de transporte), e sem trecho nao ha estimativa de
emissao. O zip anual (~150 MB) tem Viagem, Trecho, Passagem e Pagamento;
sao lidos Viagem (para filtrar o orgao 26240) e Trecho, via HTTP Range.

pls_viagens   1 doc por viagem: situacao, datas, valores de diarias,
              passagens, devolucao e outros gastos. SEM CPF, nome, cargo
              ou motivo (LGPD: o painel agrega, nao identifica pessoas).
pls_trechos   1 doc por trecho: origem/destino (cidade/UF/pais), meio de
              transporte, distancia (km, grande circulo x 1,08 -- ajuste
              DEFRA para rota real) e, para aereo, kg CO2e pelo fator da
              faixa de distancia em ref/fatores_emissao.csv.

Coordenadas dos municipios: base aberta kelvins/municipios-brasileiros
(codigo IBGE + lat/lon), baixada uma vez para data/raw/referencias/.
Trecho internacional fica sem distancia (sem coordenadas no CSV).

Chave de substituicao: `ano` (o zip anual e sempre reprocessado inteiro --
viagens do ano mudam de situacao ate a prestacao de contas).
"""

from __future__ import annotations

import math
from functools import lru_cache

import numpy as np
import pandas as pd
import requests

from common import config
from common.http import HttpClient
from common.mongo import replace_by
from common.periodo import Janela
from common.remote_zip import open_remote_zip
from common.storage import raw_path, save_processed
from common.text import norm, parse_valor, snake
from common.validation import report_counts

COL_VIAGENS = "pls_viagens"
COL_TRECHOS = "pls_trechos"
FATOR_ROTA = 1.08  # DEFRA: distancia de grande circulo subestima a rota voada

# colunas normalizadas (snake sem acento) -> nome final
VIAGEM_COLS = {
    "identificador_do_processo_de_viagem": "id_viagem",
    "situacao": "situacao",
    "viagem_urgente": "urgente",
    "codigo_orgao_solicitante": "codigo_orgao",
    "periodo_data_de_inicio": "data_inicio",
    "periodo_data_de_fim": "data_fim",
    "destinos": "destinos",
    "valor_diarias": "valor_diarias",
    "valor_passagens": "valor_passagens",
    "valor_devolucao": "valor_devolucao",
    "valor_outros_gastos": "valor_outros_gastos",
}
TRECHO_COLS = {
    "identificador_do_processo_de_viagem": "id_viagem",
    "sequencia_trecho": "sequencia",
    "origem_data": "data_origem",
    "origem_pais": "origem_pais",
    "origem_uf": "origem_uf",
    "origem_cidade": "origem_cidade",
    "destino_data": "data_destino",
    "destino_pais": "destino_pais",
    "destino_uf": "destino_uf",
    "destino_cidade": "destino_cidade",
    "meio_de_transporte": "meio_transporte",
    "numero_diarias": "numero_diarias",
}
VALORES = ["valor_diarias", "valor_passagens", "valor_devolucao", "valor_outros_gastos"]


# ---------------------------------------------------------------- leitura do zip

def _ler_csv(z, sufixo: str, colunas: dict[str, str], filtro) -> pd.DataFrame:
    nome = next((n for n in z.namelist() if n.endswith(f"_{sufixo}.csv")), None)
    if nome is None:
        raise FileNotFoundError(f"{sufixo}.csv nao encontrado no zip: {z.namelist()}")
    partes = []
    with z.open(nome) as f:
        for chunk in pd.read_csv(f, sep=";", encoding="latin-1", dtype=str, chunksize=100_000):
            chunk.columns = [snake(c) for c in chunk.columns]
            faltando = set(colunas) - set(chunk.columns)
            if faltando:
                raise KeyError(f"{nome}: colunas esperadas ausentes {sorted(faltando)}; recebidas {list(chunk.columns)}")
            chunk = chunk[list(colunas)].rename(columns=colunas)
            partes.append(chunk[filtro(chunk)])
    return pd.concat(partes, ignore_index=True) if partes else pd.DataFrame(columns=list(colunas.values()))


def _data(s: pd.Series) -> pd.Series:
    return pd.to_datetime(s, format="%d/%m/%Y", errors="coerce")


def _extrair_ano(ano: int) -> tuple[pd.DataFrame, pd.DataFrame] | None:
    url = f"{config.PORTAL_DOWNLOAD_BASE}/viagens/{ano}"
    try:
        z = open_remote_zip(url)
    except requests.HTTPError as exc:
        if exc.response is not None and exc.response.status_code == 404:
            print(f"  Viagens {ano}: arquivo nao publicado")
            return None
        raise
    print(f"  Viagens {ano}: lendo Viagem.csv (filtro orgao {config.CODIGO_ORGAO_SIAFI})...", flush=True)
    viagens = _ler_csv(z, "Viagem", VIAGEM_COLS, lambda c: c["codigo_orgao"] == config.CODIGO_ORGAO_SIAFI)
    ids = set(viagens["id_viagem"])
    print(f"  Viagens {ano}: {len(ids)} viagens da UFPB; lendo Trecho.csv...", flush=True)
    trechos = _ler_csv(z, "Trecho", TRECHO_COLS, lambda c: c["id_viagem"].isin(ids))
    return viagens, trechos


# ---------------------------------------------------------------- coordenadas e emissao

def _coordenadas() -> dict[tuple[str, str], tuple[float, float]]:
    """(cidade normalizada, UF por extenso normalizada) -> (lat, lon)."""
    client = HttpClient()
    arquivos = {}
    for nome, url in (("municipios", config.MUNICIPIOS_COORDS_URL), ("estados", config.ESTADOS_COORDS_URL)):
        path = raw_path("referencias", f"{nome}.csv")
        if not path.exists():
            path.write_bytes(client.get(url).content)
        arquivos[nome] = pd.read_csv(path, dtype=str)
    uf_nome = dict(zip(arquivos["estados"]["codigo_uf"], arquivos["estados"]["nome"].map(norm)))
    mun = arquivos["municipios"]
    return {
        (norm(n), uf_nome.get(cod)): (float(lat), float(lon))
        for n, cod, lat, lon in zip(mun["nome"], mun["codigo_uf"], mun["latitude"], mun["longitude"])
    }


def _haversine(lat1, lon1, lat2, lon2) -> np.ndarray:
    lat1, lon1, lat2, lon2 = map(np.radians, (lat1, lon1, lat2, lon2))
    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return 2 * 6371.0 * np.arcsin(np.sqrt(a))


@lru_cache
def _fatores_aereo() -> pd.DataFrame:
    fatores = pd.read_csv(config.REF_DIR / "fatores_emissao.csv", sep=";")
    fatores = fatores[fatores["meio"] == "aereo"]
    # ';' dentro do texto da fonte desloca as colunas e o fator vira texto:
    # sem esta checagem as emissoes sairiam zeradas em silencio
    if fatores.empty or not pd.api.types.is_numeric_dtype(fatores["kg_co2e_por_pkm"]):
        raise ValueError("ref/fatores_emissao.csv mal formado (sem linhas 'aereo' ou fator nao numerico -- ';' no texto?)")
    return fatores


def _fator_aereo(km: float) -> float | None:
    if km is None or math.isnan(km):
        return None
    fatores = _fatores_aereo()
    linha = fatores[(fatores["faixa_min_km"] <= km) & (km < fatores["faixa_max_km"])]
    return float(linha["kg_co2e_por_pkm"].iloc[0]) if not linha.empty else None


def _enriquecer_trechos(trechos: pd.DataFrame, coords: dict) -> pd.DataFrame:
    t = trechos.copy()

    def _xy(cidade: pd.Series, uf: pd.Series) -> tuple[pd.Series, pd.Series]:
        pts = [coords.get((norm(c), norm(u)), (np.nan, np.nan)) for c, u in zip(cidade, uf)]
        return pd.Series([p[0] for p in pts], index=cidade.index), pd.Series([p[1] for p in pts], index=cidade.index)

    lat_o, lon_o = _xy(t["origem_cidade"], t["origem_uf"])
    lat_d, lon_d = _xy(t["destino_cidade"], t["destino_uf"])
    t["distancia_km"] = (_haversine(lat_o, lon_o, lat_d, lon_d) * FATOR_ROTA).round(1)
    t["internacional"] = (t["origem_pais"].map(norm) != "brasil") | (t["destino_pais"].map(norm) != "brasil")
    t["meio_transporte"] = t["meio_transporte"].map(norm)
    aereo = t["meio_transporte"] == "aereo"
    t["kg_co2e"] = np.where(aereo, t["distancia_km"] * t["distancia_km"].map(_fator_aereo).astype(float), np.nan).round(1)
    t["numero_diarias"] = t["numero_diarias"].map(parse_valor)
    return t


# ---------------------------------------------------------------- orquestracao

def extract_transform(janela: Janela) -> tuple[pd.DataFrame, pd.DataFrame]:
    coords = _coordenadas()
    vs, ts = [], []
    for ano in janela.anos():
        extraido = _extrair_ano(ano)
        if extraido is None:
            continue
        v, t = extraido
        v["ano"] = ano
        t["ano"] = ano
        vs.append(v)
        ts.append(t)
    if not vs:
        return pd.DataFrame(), pd.DataFrame()

    viagens = pd.concat(vs, ignore_index=True)
    for col in VALORES:
        viagens[col] = viagens[col].map(parse_valor)
    ini = _data(viagens["data_inicio"])
    viagens["data_inicio"] = ini.dt.strftime("%Y-%m-%d")
    viagens["data_fim"] = _data(viagens["data_fim"]).dt.strftime("%Y-%m-%d")
    viagens["periodo"] = ini.dt.strftime("%Y-%m")
    viagens["mes"] = ini.dt.month
    viagens["urgente"] = viagens["urgente"].map(norm).eq("sim")
    viagens = viagens.drop(columns=["codigo_orgao"])

    trechos = _enriquecer_trechos(pd.concat(ts, ignore_index=True), coords)
    d = _data(trechos["data_origem"])
    trechos["data_origem"] = d.dt.strftime("%Y-%m-%d")
    trechos["data_destino"] = _data(trechos["data_destino"]).dt.strftime("%Y-%m-%d")
    trechos["periodo"] = d.dt.strftime("%Y-%m")
    trechos["mes"] = d.dt.month
    return viagens, trechos


def run(*, dry_run: bool = False, inicio: str | None = None, fim: str | None = None, **_: object) -> None:
    janela = Janela.de_args(inicio, fim)
    viagens, trechos = extract_transform(janela)
    if viagens.empty:
        print("Viagens: nada na janela")
        return

    report_counts("viagens por ano", viagens.groupby("ano").size().rename(str).to_dict())
    aereo = trechos[trechos["meio_transporte"] == "aereo"]
    sem_km = aereo["distancia_km"].isna() & ~aereo["internacional"]
    report_counts("trechos aereos", {
        "trechos": len(aereo),
        "km": round(float(aereo["distancia_km"].sum()), 1),
        "t CO2e": round(float(aereo["kg_co2e"].sum()) / 1000, 2),
        "nacionais sem coordenada": int(sem_km.sum()),
    })
    if sem_km.any():
        exemplos = aereo[sem_km][["origem_cidade", "origem_uf", "destino_cidade", "destino_uf"]].head(3)
        print(f"  exemplos sem coordenada (grafia divergente da base IBGE):\n{exemplos.to_string(index=False)}")

    if not dry_run:
        save_processed(viagens, COL_VIAGENS, replace_on="ano")
        save_processed(trechos, COL_TRECHOS, replace_on="ano")
    replace_by(COL_VIAGENS, viagens, "ano", dry_run=dry_run)
    replace_by(COL_TRECHOS, trechos, "ano", dry_run=dry_run)


if __name__ == "__main__":
    run()
