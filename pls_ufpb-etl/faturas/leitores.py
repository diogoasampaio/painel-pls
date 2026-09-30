"""Leitura do consumo nas faturas em PDF anexadas aos processos do SIPAC.

Energisa (energia): "RESUMO DAS FATURAS DE ENERGIA ELETRICA" na 1a pagina,
  uma linha por unidade consumidora (UC) com kWh faturado (ponta + fora
  ponta), demanda e valores; nas paginas seguintes, a DANF3E de cada UC,
  cujo quadro de medicao traz o kWh MEDIDO. Os dois coincidem, exceto em
  UC faturada pelo minimo (100 kWh) ou pela media -- o painel usa o medido
  quando existe. Desde 2026 o resumo usa o numero novo da UC
  ('307.568.053-41') e a DANF3E a matricula antiga: sem como casar, vale o
  kWh do resumo.
CAGEPA (agua): "FATURA AGRUPADA", uma linha por ligacao com leitura
  anterior, leitura atual, consumo medido e faturado (m3).

Os PDFs tem camada de texto (nao sao digitalizados). Conferido em 2024:
45 de 49 UCs com resumo = medido; valor bruto da CAGEPA = pago no Portal.
"""

from __future__ import annotations

import re
from pathlib import Path

import pdfplumber

NUM = r"-?[\d.]+,\d+|-?\d+"


def _br(v: str) -> float:
    return float(v.replace(".", "").replace(",", "."))


def _referencia(mm_aaaa: str | None) -> str | None:
    """'12/2023' -> '2023-12'"""
    if not mm_aaaa:
        return None
    m = re.fullmatch(r"(\d{1,2})/(\d{4})", mm_aaaa)
    return f"{m.group(2)}-{int(m.group(1)):02d}" if m else None


def _linhas_por_topo(itens: list[dict], tolerancia: float = 3) -> list[list[dict]]:
    """Agrupa palavras/caracteres da mesma linha: o `top` varia ~0,5 pt."""
    grupos: list[list[dict]] = []
    for it in sorted(itens, key=lambda i: i["top"]):
        if grupos and it["top"] - grupos[-1][0]["top"] < tolerancia:
            grupos[-1].append(it)
        else:
            grupos.append([it])
    return grupos


def ler_resumo_energisa(pagina) -> list[dict]:
    """Linhas do resumo (1a pagina). O nome da UC e impresso por cima das
    colunas Ref. e kWh quando e longo; por isso os campos numericos sao lidos
    caractere a caractere dentro da faixa x da coluna, so digitos e pontuacao.
    As colunas da direita sao alinhadas a direita: cada numero vai para o
    cabecalho que termina mais perto."""
    ws = pagina.extract_words()
    try:
        y_cab = next(w["top"] for w in ws if w["text"] == "kWh(P+FP)")
    except StopIteration:
        return []
    cab = {w["text"]: w for w in ws if abs(w["top"] - y_cab) < 2}
    fim = min((w["top"] for w in ws if w["text"].startswith("Autentica") and w["top"] > y_cab), default=pagina.height)
    faixas = {
        "referencia": (cab["Ref."]["x0"] - 7, cab["kWh(P+FP)"]["x0"] - 1),
        "kwh_faturado": (cab["kWh(P+FP)"]["x0"] - 1, cab["kWh(P+FP)"]["x1"] + 2),
        "demanda_kw": (cab["kWh(P+FP)"]["x1"] + 2, cab["Dem.(P+FP)"]["x1"] + 2),
    }
    direita = {"valor": cab["R$"]["x1"], "valor_bruto": cab["Bruto"]["x1"]}
    na_tabela = lambda i: y_cab + 5 < i["top"] < fim - 2  # noqa: E731
    palavras = [w for w in ws if na_tabela(w)]
    out = []
    for g in _linhas_por_topo([c for c in pagina.chars if na_tabela(c)]):
        topo = g[0]["top"]
        lw = sorted((w for w in palavras if abs(w["top"] - topo) < 3), key=lambda w: w["x0"])
        # numero da UC: '9980564' ate 2025; '307.568.053-41' a partir de 2026
        if len(lw) < 3 or not lw[0]["text"].isdigit() or not re.fullmatch(r"[\d.]+(?:-\d+)?", lw[1]["text"]):
            continue
        ordenados = sorted(g, key=lambda c: c["x0"])

        def campo(x0: float, x1: float, permitidos: str = "0123456789,./") -> str:
            return "".join(c["text"] for c in ordenados if x0 <= c["x0"] and c["x1"] <= x1 and c["text"] in permitidos)

        ref = re.search(r"\d{2}/\d{4}", campo(*faixas["referencia"]))
        reg = {"uc": re.sub(r"\D", "", lw[1]["text"]), "referencia": ref.group() if ref else None}
        # kWh e alinhado a direita: numero longo invade a faixa da Ref. A
        # referencia usa fonte maior (6,96 x 6,00) -- fica de fora pelo tamanho
        barra = [c for c in ordenados if c["text"] == "/" and faixas["referencia"][0] <= c["x0"] < faixas["referencia"][1]]
        tam_ref = barra[0]["size"] if barra else None
        kwh = "".join(
            c["text"] for c in ordenados
            if faixas["referencia"][0] <= c["x0"] and c["x1"] <= faixas["kwh_faturado"][1] and c["text"] in "0123456789,."
            and (tam_ref is None or abs(c["size"] - tam_ref) > 0.3)
        )
        reg["kwh_faturado"] = _br(kwh) if re.fullmatch(NUM, kwh) else None
        dem = campo(*faixas["demanda_kw"], permitidos="0123456789,.")
        reg["demanda_kw"] = _br(dem) if re.fullmatch(NUM, dem) else None
        for w in lw:
            if re.fullmatch(NUM, w["text"]) and w["x0"] > cab["ICMS"]["x0"] - 25:
                col = min(direita, key=lambda c: abs(direita[c] - w["x1"]))
                if abs(direita[col] - w["x1"]) < 15:
                    reg[col] = _br(w["text"])
        out.append(reg)
    refs = {r["referencia"] for r in out if r["referencia"]}
    for r in out:
        if not r["referencia"] and len(refs) == 1:
            r["referencia"] = next(iter(refs))
    return out


_MEDICAO = re.compile(r"Energia ativa em kWh(?: (?:Ponta|Fora Ponta))?\s+([\d.,\s]+)$", re.M)


def medido_da_pagina(texto: str) -> tuple[str, float] | None:
    """(UC, kWh medido) do quadro de medicao de uma DANF3E: soma ponta e fora
    ponta; o ultimo numero da linha e o consumo apurado. A matricula vem como
    '0009980564-2023-12-5' ou '144724-2024-4-2'."""
    m = re.search(r"MATR[ÍI]CULA:\s*0*(\d+)-\d{4}-\d{1,2}", texto)
    linhas = _MEDICAO.findall(texto)
    if not m or not linhas:
        return None
    return m.group(1), sum(_br(re.findall(NUM, linha.strip())[-1]) for linha in linhas)


def ler_medido_energisa(paginas) -> dict[str, float]:
    medido: dict[str, float] = {}
    for p in paginas:
        achou = medido_da_pagina(p.extract_text() or "")
        if achou:
            medido[achou[0]] = medido.get(achou[0], 0.0) + achou[1]
    return medido


def ler_energisa(pdf_path: Path) -> dict | None:
    with pdfplumber.open(pdf_path) as pdf:
        primeira = pdf.pages[0]
        texto = primeira.extract_text() or ""
        if "RESUMO DAS FATURAS DE ENERGIA" not in texto:
            return None
        ucs = ler_resumo_energisa(primeira)
        medido = ler_medido_energisa(pdf.pages[1:])
    numero = re.search(r"\d{2}/\d{2}/\d{4}\s+(\d{6,})\s+DS\b", texto)
    for u in ucs:
        m = medido.get(u["uc"])
        # medido so vale ate o faturado: e menor na UC cobrada pelo minimo ou pela
        # media; maior indica linha de medicao com numeros colados no PDF
        # ('420' + '53664,106' -> '42053664,106')
        fat = u["kwh_faturado"]
        u["kwh_medido"] = m if m is not None and (fat is None or m <= fat * 1.05) else None
        u["referencia"] = _referencia(u["referencia"])
    return {"fornecedor": "energisa", "fatura": numero.group(1) if numero else None, "unidades": ucs}


_LIGACAO = re.compile(
    # a partir de 2025 a ligacao e o hidrometro podem vir grudados ('81000A21AA0385351');
    # o hidrometro sempre comeca por letra
    r"^(?P<ligacao>\d+)\s*(?P<hidrometro>[A-Z][A-Z0-9]+)\s+(?P<nome>.+?)\s+(?P<leituras>(?:\d+\s+){2,4})\d{2}/\d{2}/\d{4}"
)


def ler_cagepa_texto(texto: str) -> dict | None:
    alto = texto.upper()
    if "FATURA AGRUPADA" not in alto or not ("CAGEPA" in alto or "AGUAS E ESGOTOS DA PARAIBA" in alto):
        return None
    cab = re.search(r"\d{2}/\d{2}/\d{4} \d{2}:\d{2} (\d+) (\d+) (\d{2}/\d{4}) \d{2}/\d{2}/\d{4}", texto)
    ref = _referencia(cab.group(3)) if cab else None
    unidades = []
    for linha in texto.splitlines():
        m = _LIGACAO.match(linha)
        if not m:
            continue
        n = [int(x) for x in m.group("leituras").split()]
        unidades.append({
            "uc": m.group("ligacao"), "nome": m.group("nome"), "referencia": ref,
            "leitura_anterior": n[0], "leitura_atual": n[1],
            "m3_medido": float(n[2]) if len(n) > 2 else None,
            "m3_faturado": float(n[3]) if len(n) > 3 else None,
        })
    bruto = re.search(r"TOTAL BRUTO:\s*([\d.]+,\d{2})", texto)
    return {
        "fornecedor": "cagepa", "fatura": cab.group(1) if cab else None,
        "valor_bruto": _br(bruto.group(1)) if bruto else None, "unidades": unidades,
    }


def ler_cagepa(pdf_path: Path) -> dict | None:
    with pdfplumber.open(pdf_path) as pdf:
        if "FATURA AGRUPADA" not in (pdf.pages[0].extract_text() or ""):
            return None
        return ler_cagepa_texto("\n".join(p.extract_text() or "" for p in pdf.pages))


def ler_combustivel(pdf_path: Path) -> dict | None:
    from faturas.combustivel import ler_relatorio_abastecimentos

    abastecimentos = ler_relatorio_abastecimentos(pdf_path)
    return {"fornecedor": "gerenciadora_frota", "unidades": abastecimentos} if abastecimentos else None


# Residuos de saude (B-Green/Stericycle, contrato 009/2022): relatorio de
# fiscalizacao mensal da GMA/SINFRA -- 'UFPB CAMPUS I 1760,08 Kg R$ 5,47 R$ 9.627,64';
# ate 2024 com a descricao do servico no meio e quantidade inteira ('... A, B e E 0 Kg')
_RESIDUO = re.compile(r"CAMPUS\s+(IV|III|II|I)\b[^\n]*?\s([\d.]+(?:,\d+)?)\s*Kg\s+R\$\s*([\d.]+,\d+)\s+R\$\s*([\d.]+,\d+)",
                      re.I)


def ler_residuos_texto(texto: str) -> dict | None:
    per = re.search(r"Per[íi]odo:?\s*\d{2}/(\d{2})/(\d{4})\s*a", texto)
    linhas = _RESIDUO.findall(texto)
    if not per or not linhas:
        return None
    ref = f"{per.group(2)}-{per.group(1)}"
    return {"fornecedor": "coleta_residuos", "unidades": [
        {"uc": f"CAMPUS {c.upper()}", "nome": f"Campus {c.upper()}", "referencia": ref,
         "kg": _br(kg), "valor": _br(vl), "valor_bruto": _br(vl)}
        for c, kg, _unit, vl in linhas]}


def ler_residuos(pdf_path: Path) -> dict | None:
    with pdfplumber.open(pdf_path) as pdf:
        return ler_residuos_texto("\n".join(p.extract_text() or "" for p in pdf.pages[:3]))


LEITORES = {"energia": ler_energisa, "agua": ler_cagepa, "combustivel": ler_combustivel, "residuos": ler_residuos}
