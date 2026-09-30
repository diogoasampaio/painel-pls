from __future__ import annotations

import re
import unicodedata

import pandas as pd


def strip_accents(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def norm(text: object) -> str:
    """Chave de comparacao: sem acento, minuscula, espacos colapsados."""
    if text is None or (isinstance(text, float) and pd.isna(text)):
        return ""
    return re.sub(r"\s+", " ", strip_accents(str(text)).lower()).strip()


def snake(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", norm(text)).strip("_")


def parse_valor(valor: object) -> float | None:
    """Aceita '1.234,56', '1234.56', '-1.234,56' e numeros ja convertidos."""
    if valor is None:
        return None
    if isinstance(valor, (int, float)):
        return None if pd.isna(valor) else float(valor)
    s = str(valor).strip().replace("R$", "").replace(" ", "")
    if not s:
        return None
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def leading_code(text: object) -> str | None:
    """'39 - Outros Servicos...' -> '39'. None se o texto nao comecar com codigo."""
    m = re.match(r"\s*(\d+)\s*(?:[-–.]|$)", str(text or ""))
    return m.group(1) if m else None
