"""Janela de carga (--inicio/--fim no formato AAAA-MM).

Sem argumentos, a janela e os dois ultimos meses fechados: o Portal
publica documentos com atraso de alguns dias, entao o timer mensal sempre
reprocessa tambem o mes anterior ao ultimo.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta


def _parse(ym: str) -> date:
    ano, mes = ym.split("-")
    return date(int(ano), int(mes), 1)


def _add_months(d: date, n: int) -> date:
    m = d.month - 1 + n
    return date(d.year + m // 12, m % 12 + 1, 1)


@dataclass(frozen=True)
class Janela:
    inicio: date  # primeiro dia do mes inicial
    fim: date  # primeiro dia do mes final

    @classmethod
    def de_args(cls, inicio: str | None, fim: str | None, *, hoje: date | None = None) -> "Janela":
        hoje = hoje or date.today()
        ultimo_fechado = _add_months(date(hoje.year, hoje.month, 1), -1)
        f = _parse(fim) if fim else ultimo_fechado
        i = _parse(inicio) if inicio else _add_months(f, -1)
        if i > f:
            raise ValueError(f"--inicio ({inicio}) depois de --fim ({fim})")
        return cls(i, f)

    def meses(self) -> list[str]:
        out, d = [], self.inicio
        while d <= self.fim:
            out.append(f"{d:%Y-%m}")
            d = _add_months(d, 1)
        return out

    def anos(self) -> list[int]:
        return list(range(self.inicio.year, self.fim.year + 1))

    def dias(self, *, ate: date | None = None) -> list[date]:
        ultimo = _add_months(self.fim, 1) - timedelta(days=1)
        if ate:
            ultimo = min(ultimo, ate)
        n = (ultimo - self.inicio).days + 1
        return [self.inicio + timedelta(days=k) for k in range(max(n, 0))]

    def __str__(self) -> str:
        return f"{self.inicio:%Y-%m} a {self.fim:%Y-%m}"
