"""Extracao da API do Portal da Transparencia com cache bruto em disco.

Endpoints usados (conferidos no OpenAPI em /v3/api-docs):
  /despesas/documentos            unidadeGestora + dataEmissao (1 dia) + fase
  /despesas/itens-de-empenho      codigoDocumento (NE) -> subelemento + descricao
  /despesas/empenhos-impactados   codigoDocumento (NS/OB) + fase -> empenho,
                                  subitem e valores liquidado/pago/RP

A paginacao do Portal nao informa total: pede-se `pagina` ate vir lista
vazia. Cada resposta vai para data/raw/portal/... e, dali em diante, e
lida do disco -- uma carga historica interrompida retoma de onde parou.
Documentos de um dia sao rebaixados enquanto o dia tiver menos de
PORTAL_CACHE_DIAS (o Portal publica com atraso); itens e empenhos
impactados de um documento nao mudam e ficam em cache para sempre.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from common import config
from common.http import HttpClient
from common.storage import raw_path, read_json, write_json

FASES = {1: "empenho", 2: "liquidacao", 3: "pagamento"}


class PortalApi:
    def __init__(self, *, offline: bool = False) -> None:
        """offline=True so le o cache (dry-run sem chave, testes)."""
        self.offline = offline
        if not offline and not config.PORTAL_API_KEY:
            raise RuntimeError(
                "PORTAL_API_KEY nao configurada. Cadastre a chave em "
                "https://portaldatransparencia.gov.br/api-de-dados/cadastrar-email e grave no .env"
            )
        self.client = HttpClient(headers={"chave-api-dados": config.PORTAL_API_KEY}, per_minute=config.PORTAL_RPM)
        self.cache_hits = 0
        self.cache_misses: list[str] = []
        self.calls_reportadas = 0

    @property
    def calls(self) -> int:
        return self.client.calls

    def _paginado(self, endpoint: str, params: dict[str, Any]) -> list[dict]:
        out: list[dict] = []
        pagina = 1
        while True:
            lote = self.client.get_json(f"{config.PORTAL_API_BASE}{endpoint}", {**params, "pagina": pagina})
            if not lote:
                return out
            out.extend(lote)
            pagina += 1

    def _cached(self, path: Path, fetch, *, imutavel: bool) -> list[dict]:
        if path.exists() and (imutavel or self.offline):
            self.cache_hits += 1
            return read_json(path)
        if self.offline:
            self.cache_misses.append(str(path.relative_to(config.RAW_DIR)))
            return []
        data = fetch()
        write_json(path, data)
        return data

    def documentos(self, ug: str, fase: int, dia: date) -> list[dict]:
        path = raw_path("portal", "documentos", ug, FASES[fase], f"{dia:%Y}", f"{dia:%Y-%m-%d}.json")
        imutavel = (date.today() - dia).days > config.PORTAL_CACHE_DIAS
        return self._cached(
            path,
            lambda: self._paginado(
                "/despesas/documentos", {"unidadeGestora": ug, "dataEmissao": f"{dia:%d/%m/%Y}", "fase": fase}
            ),
            imutavel=imutavel,
        )

    def itens_empenho(self, documento: str) -> list[dict]:
        path = raw_path("portal", "itens_empenho", _ano_doc(documento), f"{documento}.json")
        return self._cached(
            path, lambda: self._paginado("/despesas/itens-de-empenho", {"codigoDocumento": documento}), imutavel=True
        )

    def empenhos_impactados(self, documento: str, fase: int) -> list[dict]:
        path = raw_path("portal", "empenhos_impactados", FASES[fase], _ano_doc(documento), f"{documento}.json")
        return self._cached(
            path,
            lambda: self._paginado("/despesas/empenhos-impactados", {"codigoDocumento": documento, "fase": fase}),
            imutavel=True,
        )


def _ano_doc(documento: str) -> str:
    # 153065152612025NE000123 -> 2025 (UG 6 + gestao 5 + ano 4 + tipo 2 + num)
    ano = documento[11:15]
    return ano if ano.isdigit() else "outros"
