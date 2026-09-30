"""Consulta publica de processos do SIPAC da UFPB (sipac.ufpb.br/public).

Sem login e sem CAPTCHA: o formulario "Consultar Processos" do portal
publico aceita o numero do processo e devolve o link do processo
detalhado, que lista os documentos -- os ostensivos com arquivo tem link
direto de download (verArquivoDocumento).

O formulario e JSF: a pagina de consulta so abre por postback a partir do
portal (com o ViewState da sessao). Por isso cada busca refaz portal ->
formulario -> consulta na mesma sessao.

Numero do processo: o Portal da Transparencia publica sem o radical da
UFPB ('004049/2024-54'); no SIPAC e 23074.004049/2024-54.
"""

from __future__ import annotations

import re
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from common import config
from common import http  # noqa: F401  (injeta truststore)
from common.http import USER_AGENT

RADICAL_UFPB = "23074"


class Sipac:
    def __init__(self, base: str | None = None, pausa: float | None = None) -> None:
        self.base = base or config.SIPAC_BASE
        self.pausa = config.SIPAC_PAUSA_S if pausa is None else pausa
        self.s = requests.Session()
        self.s.headers["User-Agent"] = USER_AGENT
        self.requisicoes = 0

    def _req(self, metodo: str, url: str, **kw) -> requests.Response:
        time.sleep(self.pausa)  # servidor da universidade: uma requisicao por vez, sem rajada
        self.requisicoes += 1
        r = self.s.request(metodo, url, timeout=120, **kw)
        r.raise_for_status()
        return r

    def _form_consulta(self) -> dict[str, str]:
        soup = BeautifulSoup(self._req("GET", self.base + "/public/jsp/portal.jsf").text, "html.parser")
        link = next(a for a in soup.find_all("a") if "Consultar Processos" in a.get_text())
        m = re.search(r"getElementById\('([^']+)'\),\{'([^']+)':'([^']+)'", link["onclick"])
        form = soup.find("form", id=m.group(1))
        data = {i["name"]: i.get("value", "") for i in form.find_all("input") if i.get("name")}
        data[m.group(2)] = m.group(3)
        soup = BeautifulSoup(self._req("POST", self.base + form["action"], data=data).text, "html.parser")
        f = soup.find("form", id="processoForm")
        return {i["name"]: i.get("value", "") for i in f.find_all("input") if i.get("name") and i.get("type") != "radio"}

    def buscar(self, processo: str) -> dict | None:
        """'004049/2024-54' -> {'id': 2113821, 'numero': '23074.004049/2024-54', 'assunto': ...}"""
        m = re.fullmatch(r"(\d+)/(\d{4})-(\d+)", processo.strip())
        if not m:
            return None
        num, ano, dv = m.groups()
        # o Portal as vezes grava o numero sem zero a esquerda ('04533/2024-45')
        # ou com digitos a mais no DV ('042864/2024-3752'): o DV tem 2 digitos
        num, dv = num.zfill(6), dv[:2]
        html = self._consultar(num, ano, dv)
        achou = re.search(r"processo_detalhado\.jsf\?id=(\d+)", html)
        if not achou and dv != "99":
            # DV errado no Portal: o SIPAC aceita '99' no lugar do DV e busca so pelo numero/ano
            html = self._consultar(num, ano, "99")
            achou = re.search(r"processo_detalhado\.jsf\?id=(\d+)", html)
        if not achou:
            return None
        linha = BeautifulSoup(html, "html.parser").find("a", href=re.compile("processo_detalhado")).find_parent("tr")
        tds = linha.find_all("td")
        return {
            "id": int(achou.group(1)),
            "numero": tds[0].get_text(strip=True),
            "assunto": tds[1].get_text(" ", strip=True) if len(tds) > 1 else "",
        }

    def _consultar(self, num: str, ano: str, dv: str) -> str:
        data = self._form_consulta()
        data.update(tipo_consulta="100", RADICAL_PROTOCOLO=RADICAL_UFPB, NUM_PROTOCOLO=num, ANO_PROTOCOLO=ano, DV_PROTOCOLO=dv)
        return self._req("POST", self.base + "/public/jsp/processos/consulta_processo.jsf", data=data).text

    def documentos(self, id_processo: int) -> list[dict]:
        html = self._req("GET", f"{self.base}/public/jsp/processos/processo_detalhado.jsf?id={id_processo}").text
        docs = []
        for tr in BeautifulSoup(html, "html.parser").find_all("tr"):
            tds = tr.find_all("td")
            if len(tds) < 5 or not tds[0].get_text(strip=True).isdigit():
                continue
            arq = tr.find("a", href=re.compile("verArquivoDocumento"))
            docs.append({
                "ordem": int(tds[0].get_text(strip=True)),
                "especie": tds[1].get_text(" ", strip=True),
                "data": tds[2].get_text(strip=True),
                "arquivo": self.base + arq["href"] if arq else None,
            })
        return docs

    def nome_arquivo(self, url: str) -> str:
        """Nome do arquivo anexado (cabecalho Content-Disposition), sem baixar."""
        r = self._req("HEAD", url, allow_redirects=True)
        m = re.search(r'filename="?([^";]+)', r.headers.get("content-disposition", ""))
        return m.group(1) if m else ""

    def baixar(self, url: str, destino: Path) -> Path:
        destino.parent.mkdir(parents=True, exist_ok=True)
        tmp = destino.with_suffix(".tmp")
        tmp.write_bytes(self._req("GET", url).content)
        tmp.replace(destino)
        return destino
