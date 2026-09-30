"""Cliente HTTP compartilhado pelos modulos.

- truststore: download.inep.gov.br (e outros *.gov.br) nao envia a cadeia
  intermediaria do certificado; o bundle do certifi recusa, o repositorio
  do Windows/macOS completa a cadeia. Injetado uma vez, na importacao.
- RateLimiter: o Portal da Transparencia bloqueia a chave (HTTP 429) acima
  do limite por minuto. Espacamento fixo entre chamadas e mais previsivel
  do que reagir so ao 429.
"""

from __future__ import annotations

import time
from typing import Any

import requests

try:
    import truststore

    truststore.inject_into_ssl()
except ImportError:  # pragma: no cover - dependencia declarada em requirements
    pass

USER_AGENT = "PLS-UFPB-ETL/1.0 (painel de sustentabilidade; +https://www.ufpb.br)"


class RateLimiter:
    def __init__(self, per_minute: int) -> None:
        self.interval = 60.0 / per_minute if per_minute > 0 else 0.0
        self._last = 0.0

    def wait(self) -> None:
        delta = time.monotonic() - self._last
        if delta < self.interval:
            time.sleep(self.interval - delta)
        self._last = time.monotonic()


class HttpClient:
    def __init__(
        self,
        *,
        headers: dict[str, str] | None = None,
        per_minute: int = 0,
        timeout: int = 60,
        max_retries: int = 5,
    ) -> None:
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT, "Accept": "application/json"})
        if headers:
            self.session.headers.update(headers)
        self.limiter = RateLimiter(per_minute)
        self.timeout = timeout
        self.max_retries = max_retries
        self.calls = 0

    def get(self, url: str, params: dict[str, Any] | None = None, **kwargs: Any) -> requests.Response:
        last: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            self.limiter.wait()
            self.calls += 1
            try:
                resp = self.session.get(url, params=params, timeout=self.timeout, **kwargs)
            except requests.RequestException as exc:
                last = exc
                time.sleep(2 * attempt)
                continue
            if resp.status_code == 429 or resp.status_code >= 500:
                # 429 no Portal = cota do minuto estourada; esperar o minuto virar.
                time.sleep(60 if resp.status_code == 429 else 3 * attempt)
                last = requests.HTTPError(f"{resp.status_code} em {resp.url}", response=resp)
                continue
            resp.raise_for_status()
            return resp
        raise RuntimeError(f"Falha apos {self.max_retries} tentativas: {url} {params}") from last

    def get_json(self, url: str, params: dict[str, Any] | None = None) -> Any:
        resp = self.get(url, params=params)
        return resp.json() if resp.text.strip() else None
