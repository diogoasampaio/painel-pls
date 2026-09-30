"""Arquivos diarios de despesas do Portal da Transparencia (dados abertos).

  https://portaldatransparencia.gov.br/download-de-dados/despesas/AAAAMMDD
  -> redireciona para dadosabertos-download.cgu.gov.br/.../AAAAMMDD_Despesas.zip

Cada zip traz o governo federal inteiro naquele dia (~5-30 MB). Interessam:
  Empenho, ItemEmpenho, Liquidacao, Liquidacao_EmpenhosImpactados,
  Pagamento, Pagamento_EmpenhosImpactados

Vantagens sobre a API: sem limite de requisicoes, codigos de natureza ja
vem prontos ("Codigo Natureza Despesa Completa") e o item de empenho traz
Quantidade e Valor Unitario em colunas.

Do zip so as linhas da UFPB (UGS) vao para o cache em
data/raw/portal_bulk/<ano>/<dia>.json -- o zip inteiro nao e guardado (um
ano daria varios GB). Dia ainda nao publicado (404) devolve None e o
chamador cai para a API.

O servidor da CGU passa a responder 405 para o IP inteiro depois de ~25
downloads seguidos (visto em 2026-09). Por isso: ritmo limitado
(PORTAL_BULK_RPM), cada dia baixado uma unica vez, e ao ser bloqueado o
ETL pausa (PORTAL_BULK_PAUSA_S) e tenta de novo; se continuar bloqueado,
para de baixar e segue com o que esta em cache -- os dias que faltaram
ficam "sem dados" e o mes nao e gravado ate a proxima execucao.

Arquivo de um dia so recusado (403 com o dia seguinte saindo normalmente,
visto em 2022-03-27): nao e bloqueio. O dia fica marcado "indisponivel" no
cache, com zero linhas, e a carga segue -- apague o .json para tentar de novo.
"""

from __future__ import annotations

import io
import time
import zipfile
from datetime import date, timedelta

import pandas as pd
import requests

from common import config
from common.http import HttpClient
from common.storage import raw_path, read_json, write_json
from common.text import snake

# chave interna -> sufixo do CSV dentro do zip
ARQUIVOS = {
    "empenho": "Despesas_Empenho",
    "item_empenho": "Despesas_ItemEmpenho",
    "liquidacao": "Despesas_Liquidacao",
    "liquidacao_impactados": "Despesas_Liquidacao_EmpenhosImpactados",
    "pagamento": "Despesas_Pagamento",
    "pagamento_impactados": "Despesas_Pagamento_EmpenhosImpactados",
}


class PortalBulk:
    def __init__(self, *, offline: bool = False) -> None:
        self.offline = offline
        self.client = HttpClient(per_minute=config.PORTAL_BULK_RPM, timeout=300)
        self.client.session.headers["Accept"] = "*/*"
        self.downloads = 0
        self.cache_hits = 0
        self.nao_publicados: list[date] = []
        # arquivo do dia que o Portal recusa sempre (403), com os dias vizinhos saindo
        # normalmente -- visto em 2022-03-27. Fica marcado no cache e nao trava a carga.
        self.indisponiveis: list[date] = []
        self.bloqueado = False

    def dia(self, dia: date) -> dict[str, list[dict]] | None:
        path = raw_path("portal_bulk", f"{dia:%Y}", f"{dia:%Y-%m-%d}.json")
        imutavel = (date.today() - dia).days > config.PORTAL_CACHE_DIAS
        if path.exists() and (imutavel or self.offline):
            cache = read_json(path)
            # o cache so guarda as linhas das UGs da epoca; se UGS mudou, baixa de novo
            if isinstance(cache, dict) and set(config.UGS) <= set(cache.get("ugs", [])):
                self.cache_hits += 1
                if cache.get("indisponivel"):
                    self.indisponiveis.append(dia)
                return cache["dados"]
            if self.offline:
                return None
        if self.offline or self.bloqueado:
            return None

        url = f"{config.PORTAL_DOWNLOAD_BASE}/despesas/{dia:%Y%m%d}"
        for tentativa in range(config.PORTAL_BULK_TENTATIVAS + 1):
            try:
                resp = self.client.get(url)
                break
            except requests.HTTPError as exc:
                status = exc.response.status_code if exc.response is not None else None
                if status == 404:
                    self.nao_publicados.append(dia)
                    return None
                if status not in (403, 405):
                    raise
                if self._so_este_dia(dia):
                    self.indisponiveis.append(dia)
                    print(f"  arquivo de {dia} recusado pelo Portal ({status}) com o dia seguinte disponivel: "
                          "marcado como indisponivel (apague o .json para tentar de novo)", flush=True)
                    write_json(path, {"ugs": sorted(config.UGS), "indisponivel": status, "dados": {k: [] for k in ARQUIVOS}})
                    return {k: [] for k in ARQUIVOS}
                motivo = f"CGU bloqueou o download ({status})"
            except (requests.ConnectionError, RuntimeError) as exc:
                # queda de rede/DNS (visto em 2026-09) ou 5xx persistente:
                # transitorio, mesmo tratamento do bloqueio
                motivo = f"sem conexao com o Portal ({type(exc.__cause__ or exc).__name__})"
            if tentativa == config.PORTAL_BULK_TENTATIVAS:
                self.bloqueado = True
                print(f"  {motivo} em {dia}, de novo: parando os downloads nesta execucao; "
                      "o que ja foi baixado fica em data/raw/portal_bulk/ e a proxima execucao retoma daqui", flush=True)
                return None
            print(f"  {motivo} em {dia}; pausa de {config.PORTAL_BULK_PAUSA_S // 60} min", flush=True)
            time.sleep(config.PORTAL_BULK_PAUSA_S)
        self.downloads += 1
        dados = _filtrar_zip(resp.content)
        write_json(path, {"ugs": sorted(config.UGS), "dados": dados})
        return dados

    def _so_este_dia(self, dia: date) -> bool:
        """403/405 so neste arquivo? Pede os primeiros bytes do dia seguinte:
        se vierem, o servidor nao esta bloqueando -- o arquivo do dia e que falha."""
        vizinho = dia + timedelta(days=1)
        if vizinho >= date.today():
            return False
        try:
            r = self.client.session.get(f"{config.PORTAL_DOWNLOAD_BASE}/despesas/{vizinho:%Y%m%d}",
                                        headers={"Range": "bytes=0-100"}, timeout=60, allow_redirects=True)
        except requests.RequestException:
            return False
        return r.status_code in (200, 206)


def _filtrar_zip(conteudo: bytes) -> dict[str, list[dict]]:
    ugs = set(config.UGS)
    out: dict[str, list[dict]] = {}
    with zipfile.ZipFile(io.BytesIO(conteudo)) as z:
        for chave, sufixo in ARQUIVOS.items():
            nome = next((n for n in z.namelist() if n.endswith(f"_{sufixo}.csv")), None)
            if nome is None:
                out[chave] = []
                continue
            partes = []
            with z.open(nome) as f:
                for chunk in pd.read_csv(f, sep=";", encoding="latin-1", dtype=str, chunksize=200_000):
                    chunk.columns = [snake(c) for c in chunk.columns]
                    partes.append(chunk[_filtro_ufpb(chunk, ugs)])
            df = pd.concat(partes, ignore_index=True)
            out[chave] = df.astype(object).where(df.notna(), None).to_dict(orient="records")
    return out


def _filtro_ufpb(df: pd.DataFrame, ugs: set[str]) -> pd.Series:
    if "codigo_unidade_gestora" in df:
        return df["codigo_unidade_gestora"].isin(ugs)
    # arquivos sem coluna de UG (itens, empenhos impactados): o codigo do
    # documento comeca pelos 6 digitos da UG emitente. Nos impactados vale o
    # documento (liquidacao/pagamento), nao o empenho -- dai a ordem.
    for col in ("codigo_liquidacao", "codigo_pagamento", "codigo_empenho"):
        if col in df:
            return df[col].str[:6].isin(ugs)
    raise KeyError(f"arquivo sem coluna para filtrar a UG: {list(df.columns)}")
