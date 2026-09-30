"""Leitura de ZIP remoto via HTTP Range, sem baixar o arquivo inteiro.

Os microdados do INEP tem ~450 MB, mas o arquivo de IES tem 1 MB; os
zips de Viagens do Portal tem ~150 MB e so 3 dos 4 CSVs interessam.
`zipfile` so precisa de um objeto seekable -- este adaptador traduz cada
read() em um GET com cabecalho Range. Leitura sequencial usa buffer
grande para nao virar milhares de requisicoes pequenas.
"""

from __future__ import annotations

import io
import time
import zipfile

import requests

from . import config
from . import http  # noqa: F401  (injeta truststore)
from .http import USER_AGENT


class HttpRangeFile(io.RawIOBase):
    def __init__(self, url: str, timeout: int = 300) -> None:
        self.session = requests.Session()
        self.session.headers["User-Agent"] = USER_AGENT
        self.timeout = timeout
        head = self._retry(lambda: self.session.head(url, timeout=timeout, allow_redirects=True))
        if head.headers.get("Accept-Ranges") != "bytes":
            raise RuntimeError(f"Servidor nao aceita Range: {url}")
        self.url = head.url  # segue o redirect do Portal para o bucket da CGU
        self.size = int(head.headers["Content-Length"])
        self.pos = 0

    @staticmethod
    def _retry(call, attempts: int = 5) -> requests.Response:
        # download.inep.gov.br derruba conexoes TLS de forma intermitente
        # (ConnectionResetError 10054); a mesma chamada passa na seguinte.
        # A CGU bloqueia o IP (403/405) depois de muitas requisicoes seguidas
        # -- mesma pausa do download de despesas (ver despesas/portal_bulk.py).
        bloqueios = 0
        attempt = 0
        while attempt < attempts:
            attempt += 1
            try:
                resp = call()
            except requests.ConnectionError:
                if attempt == attempts:
                    raise
                time.sleep(3 * attempt)
                continue
            if resp.status_code in (403, 405) and bloqueios < config.PORTAL_BULK_TENTATIVAS:
                bloqueios += 1
                attempt -= 1
                print(f"  servidor bloqueou a leitura ({resp.status_code}); pausa de {config.PORTAL_BULK_PAUSA_S // 60} min", flush=True)
                time.sleep(config.PORTAL_BULK_PAUSA_S)
                continue
            if resp.status_code < 500 or attempt == attempts:
                resp.raise_for_status()  # 404 (ano ainda nao publicado) sai na hora
                return resp
            time.sleep(3 * attempt)
        raise AssertionError("inalcancavel")

    def readable(self) -> bool:
        return True

    def seekable(self) -> bool:
        return True

    def tell(self) -> int:
        return self.pos

    def seek(self, offset: int, whence: int = io.SEEK_SET) -> int:
        base = {io.SEEK_SET: 0, io.SEEK_CUR: self.pos, io.SEEK_END: self.size}[whence]
        self.pos = base + offset
        return self.pos

    def readinto(self, buffer) -> int:  # type: ignore[override]
        n = min(len(buffer), self.size - self.pos)
        if n <= 0:
            return 0
        rng = {"Range": f"bytes={self.pos}-{self.pos + n - 1}"}
        resp = self._retry(lambda: self.session.get(self.url, headers=rng, timeout=self.timeout))
        data = resp.content
        buffer[: len(data)] = data
        self.pos += len(data)
        return len(data)


def open_remote_zip(url: str, buffer_size: int = 8 << 20) -> zipfile.ZipFile:
    return zipfile.ZipFile(io.BufferedReader(HttpRangeFile(url), buffer_size=buffer_size))
