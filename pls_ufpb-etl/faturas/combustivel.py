"""Relatorio de abastecimentos da gerenciadora de frota (anexo dos processos
de pagamento de combustivel no SIPAC).

O relatorio ("Abastecimentos: Cod. Transacao | Data/Hora | Unidade |
Subunidade | ... | Combustivel/Servico | Condutor | ... | Qtde (L) | Preco
Unitario | Valor Bruto | ... | Km Rodado | KML ...") e uma tabela larga em
que cada celula quebra em varias linhas. Cada abastecimento comeca na linha
com o codigo da transacao na 1a coluna; as colunas sao separadas pela posicao
x dos cabecalhos.

LGPD: condutor, registro e cartao NAO saem daqui -- o painel agrega por
combustivel, subunidade e mes. A placa fica (bem publico) para permitir
contar veiculos e km/L da frota.
"""

from __future__ import annotations

import re
from pathlib import Path

import pdfplumber

# Layouts do relatorio (a gerenciadora mudou o modelo algumas vezes). Cada um:
# coluna -> (regex do cabecalho, ocorrencia); cabecalhos a ignorar (2a palavra
# de um cabecalho de varias palavras); folga = quantos pontos os valores
# comecam antes do cabecalho (None: fronteira no ponto medio entre cabecalhos).
LAYOUTS = [
    {   # PRIME 2024-2025 "Abastecimentos"; em 2026 ganhou 2a coluna de preco e
        # 4a de valor: bruto = 1o "Valor", liquido = ultimo
        "campos": {
            "transacao": ("Cód", 0), "data": ("Data", 0), "subunidade": ("Subuni", 0), "placa": ("Placa", 0),
            "combustivel": ("Comb", 0), "estabelecimento": ("Estabe", 0), "cidade": ("Cidade", 0), "uf": ("UF", 0),
            "cnpj_posto": ("CNPJ", 0), "litros": ("Qtde", 0), "preco_litro": ("Preco", 0),
            "valor_bruto": ("Valor", 0), "valor_liquido": ("Valor", -1), "km_rodado": ("Km$", 0), "km_por_litro": ("KML", 0),
        },
        "ignorar": {"de"}, "folga": None,
    },
    {   # PRIME out-nov/2025 "Relatorio de Abastecimento/Faturamento": 37 colunas
        # estreitas, cabecalhos cortados ("Quan t. (L)", "Subu nidad e")
        "campos": {
            "transacao": ("Cód", 0), "data": ("Data", 0), "placa": ("Placa", 0), "litros": ("Quan", 0),
            "preco_litro": ("Pre(?!f)", 0), "valor_bruto": ("Valor", 0), "subunidade": ("Subu", 0),
            "combustivel": ("Servi", 0), "estabelecimento": ("Nome", 0), "cnpj_posto": ("CNPJ", 0),
            "cidade": ("Cidad", 0), "km_por_litro": ("KM/H", 0), "km_rodado": ("KM$", 0),
        },
        "ignorar": set(), "folga": None,
    },
    {   # PRIME dez/2025 "Conferencia NFe ANP"
        "campos": {
            "transacao": ("Cód", 0), "data": ("Data", 0), "placa": ("Placa", 0), "subunidade": ("Unidade", 0),
            "estabelecimento": ("Nome", 0), "cidade": ("Cidade", 0), "combustivel": ("Combust", 0),
            "litros": ("Qtde", 0), "valor_bruto": ("Valor", 0), "preco_litro": ("Valor", 1), "valor_liquido": ("Valor", -1),
        },
        "ignorar": {"Venda", "do", "Posto", "Litro", "c/"}, "folga": 9,
    },
]
NUMERICAS = {"litros", "preco_litro", "valor_bruto", "valor_liquido", "km_rodado", "km_por_litro"}


def _br(v: str) -> float | None:
    v = v.strip()
    if not re.fullmatch(r"-?[\d.]*,?\d+", v):
        return None
    return float(v.replace(".", "").replace(",", "."))


def tipo_combustivel(texto: str) -> str:
    t = texto.upper()
    if "DIESEL" in t:
        return "diesel"
    if "GASOL" in t:
        return "gasolina"
    if "ETANOL" in t or "ALCOOL" in t or "ÁLCOOL" in t:
        return "etanol"
    if "GNV" in t or "GAS NATURAL" in t:
        return "gnv"
    if "ARLA" in t:
        return "arla"
    return "outro"


def _limites(ws: list[dict]) -> tuple[float, list[tuple[float, str | None]]] | None:
    try:
        y = next(w["top"] for w in ws if w["text"].startswith("Cód") and w["x0"] < 60)
    except StopIteration:
        return None
    linha = sorted((w for w in ws if abs(w["top"] - y) < 2), key=lambda w: w["x0"])
    faltam = []
    for lay in LAYOUTS:
        cab = [w for w in linha if w["text"] not in lay["ignorar"]]
        textos = [w["text"] for w in cab]
        nomes: list[str | None] = [None] * len(cab)
        try:
            for campo, (padrao, ocorrencia) in lay["campos"].items():
                # diferencia maiusculas: 'Km' nao casa com 'KML' nem 'KM'
                nomes[[i for i, t in enumerate(textos) if re.match(padrao, t)][ocorrencia]] = campo
        except IndexError:
            faltam.append(padrao)
            continue
        xs = [w["x0"] for w in cab]
        if lay["folga"] is None:
            # os valores comecam alguns pontos antes do cabecalho: a fronteira
            # entre duas colunas e o ponto medio entre os inicios dos cabecalhos
            inicio = [0.0] + [(a + b) / 2 for a, b in zip(xs, xs[1:])]
        else:
            inicio = [0.0] + [x - lay["folga"] for x in xs[1:]]
        return y, list(zip(inicio, nomes))
    raise ValueError(f"layout de relatorio desconhecido (faltam {faltam}): {[w['text'] for w in linha]}")


def ler_pagina(pagina) -> list[dict]:
    ws = pagina.extract_words()
    lim = _limites(ws)
    if not lim:
        return []
    y_cab, cols = lim
    corpo = [w for w in ws if w["top"] > y_cab + 20]
    # rodape com totais da pagina/relatorio: fica fora do ultimo abastecimento
    rodape = [w["top"] for w in corpo if re.match(r"(Total|Quant\.)", w["text"])]
    if rodape:
        corpo = [w for w in corpo if w["top"] < min(rodape) - 1]
    inicios = sorted({round(w["top"], 1) for w in corpo if w["x0"] < cols[1][0] and re.fullmatch(r"\d+", w["text"])})
    out = []
    for i, topo in enumerate(inicios):
        fim = inicios[i + 1] if i + 1 < len(inicios) else float("inf")
        bloco = sorted((w for w in corpo if topo - 1 <= w["top"] < fim - 1), key=lambda w: (round(w["top"]), w["x0"]))
        reg: dict[str, str] = {}
        for w in bloco:
            idx = max(j for j, (x, _) in enumerate(cols) if w["x0"] >= x)
            nome = cols[idx][1]
            if nome:
                reg[nome] = reg.get(nome, "") + w["text"]
        if "litros" not in reg:
            continue
        d = re.match(r"(\d{2})/(\d{2})/(\d{4})", reg.get("data", ""))
        rec = {
            "transacao": reg.get("transacao"),
            "data": f"{d.group(3)}-{d.group(2)}-{d.group(1)}" if d else None,
            "subunidade": reg.get("subunidade"),
            "placa": reg.get("placa"),
            "combustivel_texto": reg.get("combustivel", ""),
            "combustivel": tipo_combustivel(reg.get("combustivel", "")),
            "estabelecimento": reg.get("estabelecimento"),
            "cidade": reg.get("cidade"), "uf": reg.get("uf"), "cnpj_posto": reg.get("cnpj_posto"),
        }
        for c in NUMERICAS:
            rec[c] = _br(reg.get(c, ""))
        out.append(rec)
    return out


# NF de servico da PRIME (documento NOTA do processo): quando o processo nao tem
# o relatorio de abastecimentos (jun-ago/2024 so trazem tickets em R$), a NF da
# os litros do mes por combustivel -- '4521,923 UM CONSUMO GESTAO DE FROTA
# GASOLINA 5,926238 26.797,99' -- e o periodo nas observacoes ('PERIODO DE
# 01/06/2024 A 30/06/2024'). Sem placa nem subunidade: fica no Campus I.
_NOTA_ITEM = re.compile(r"^([\d.]*\d,\d+)\s+UM\s+CONSUMO GEST[AÃ]O DE FROTA\s+(.+?)\s+([\d.]*\d,\d+)\s+([\d.]*\d,\d{2})$",
                        re.M | re.I)
_NOTA_PERIODO = re.compile(r"PER[IÍ]ODO DE (\d{2})/(\d{2})/(\d{4}) A", re.I)


def ler_nota_prime(texto: str) -> list[dict]:
    per = _NOTA_PERIODO.search(texto)
    if not per:
        return []
    data = f"{per.group(3)}-{per.group(2)}-01"
    return [{"transacao": None, "data": data, "subunidade": "CAMPUS1", "placa": None,
             "combustivel_texto": prod.strip(), "combustivel": tipo_combustivel(prod),
             "litros": _br(qt), "preco_litro": _br(unit), "valor_bruto": _br(total), "valor_liquido": _br(total)}
            for qt, prod, unit, total in _NOTA_ITEM.findall(texto)]


def ler_relatorio_abastecimentos(pdf_path: Path) -> list[dict]:
    with pdfplumber.open(pdf_path) as pdf:
        texto = pdf.pages[0].extract_text() or ""
        if re.search(r"CONSUMO GEST[AÃ]O DE FROTA", texto, re.I):
            return ler_nota_prime(texto)
        if "EXTRATO DE FATURAMENTO" in texto:
            return ler_extrato_goldi(pdf)
        if "CLIENTE_NOME" in texto and "PRODUTO_NOME" in texto:
            return ler_planilha_goldi(pdf)
        if not re.search(r"Abastecimento|Conferência NFe", texto):
            return []
        linhas = []
        for p in pdf.pages:
            linhas += ler_pagina(p)
    return linhas


# GOLDI (gerenciadora ate mai/2024, contrato 008/2019): "EXTRATO DE FATURAMENTO",
# uma fatura por empenho/departamento; o texto vem sem espacos entre palavras.
# Linha: '01/12/2313:13 VEICULO Motorista Estabelecimento 68,000 6,010 408,68 16,55 392,13'
# (qtde, unitario, total, desconto, liquido), sob o cabecalho do produto ('DieselS10').
# Em 2024: ano com 4 digitos ('20/05/202412:08'), estabelecimento antes do
# veiculo e total/desconto com 3 decimais.
# A linha e lida pelo inicio (data) e pelos 5 ultimos tokens numericos.
_GOLDI = re.compile(r"^(\d{2})/(\d{2})/(\d{4}|\d{2})\d{2}:\d{2}\s")
_NUM_GOLDI = re.compile(r"-?[\d.]*\d,\d{2,3}")
# 2022 e inicio de 2023: 'DieselS10 16/12/2209:37 VEICULO Motorista Estab 35,000 6,380 223,30'
_GOLDI_ANTIGO = re.compile(r"^(\S+)\s(\d{2})/(\d{2})/(\d{2})\d{2}:\d{2}\s")
_PRODUTO = re.compile(r"^(diesel|gasolina|etanol|[aá]lcool|arla|gnv)", re.I)
_PLACA = re.compile(r"[A-Z]{3}-?\d[A-Z0-9]\d{2}")


def _reg_goldi(fatura, n, dd, mm, aa, depto, placa, produto, qt, unit, total, liq) -> dict:
    return {
        "transacao": f"goldi-{fatura}-{n}", "data": f"{aa if len(aa) == 4 else '20' + aa}-{mm}-{dd}",
        "subunidade": depto, "placa": placa.group(0) if placa else None,
        "combustivel_texto": produto, "combustivel": tipo_combustivel(produto),
        "estabelecimento": None, "cidade": None, "uf": None, "cnpj_posto": None,
        "litros": _br(qt), "preco_litro": _br(unit), "valor_bruto": _br(total),
        "valor_liquido": _br(liq) if liq else None, "km_rodado": None, "km_por_litro": None,
    }


# Planilha "Analise de Consumo da Frota" da GOLDI (2023): usada quando a fatura veio
# escaneada. Uma linha por abastecimento, sem departamento (campus fica em branco):
# '... OFA-6531 01/03/2023 07:10FULANO ... Gasolina Comum 42,46 R$ 4,97 R$ 211,03'
_PLANILHA_GOLDI = re.compile(
    r"(?P<placa>[A-Z]{3}-?\d[A-Z0-9]\d{2})\s+(?P<d>\d{2})/(?P<m>\d{2})/(?P<a>\d{4})\s?\d{2}:\d{2}.*?"
    r"\s(?P<prod>(?:Gasolina|Diesel|Etanol|[AÁ]lcool|Arla|GNV)[A-Za-z0-9 ]*?)\s+"
    r"(?P<qt>[\d.]+(?:,\d+)?)\s+R\$\s?(?P<unit>[\d.]+,\d+)\s+R\$\s?(?P<tot>[\d.]+,\d+)\s*$")


def ler_planilha_goldi(pdf) -> list[dict]:
    out = []
    for p in pdf.pages:
        for ln in (p.extract_text() or "").splitlines():
            m = _PLANILHA_GOLDI.search(ln)
            if not m or not _br(m["tot"]):
                continue
            out.append({
                **_reg_goldi("plan", len(out), m["d"], m["m"], m["a"], None,
                             re.match(r".+", m["placa"]), m["prod"], m["qt"], m["unit"], m["tot"], None),
                "transacao": f"goldi-plan-{m['placa']}-{m['a']}{m['m']}{m['d']}-{len(out)}",
            })
    return out


def ler_extrato_goldi(pdf) -> list[dict]:
    out, depto, fatura, produto = [], None, None, ""
    for p in pdf.pages:
        # o extrato traz ~20 mil tracos vetoriais por pagina: so os caracteres importam
        so_texto = p.filter(lambda o: o.get("object_type") == "char") if hasattr(p, "filter") else p
        for ln in (so_texto.extract_text() or "").splitlines():
            if m := re.match(r"Departamento:\s*([A-Z]+)", ln):
                depto = m.group(1)
            elif m := re.search(r"\(ID:(\d+)\)", ln):
                fatura = m.group(1)
            elif _PRODUTO.match(ln) and not re.search(r"\d{2}/\d{2}", ln):
                produto = ln
            elif (m := _GOLDI_ANTIGO.match(ln)) and len(nums := ln.split()[-3:]) == 3 and all(
                    _NUM_GOLDI.fullmatch(n) for n in nums):
                # ate o inicio de 2023: produto no inicio da linha e so qtde, unitario e
                # total -- o desconto vem no total da fatura, nao por abastecimento
                prod, dd, mm, aa = m.groups()
                qt, unit, total = nums
                if _br(total) <= 0 or tipo_combustivel(prod) in ("outro", "arla"):
                    continue  # taxa de administracao, desconto ou servico
                placa = _PLACA.search(ln)
                out.append(_reg_goldi(fatura, len(out), dd, mm, aa, depto, placa, prod, qt, unit, total, None))
            elif (m := _GOLDI.match(ln)) and len(nums := ln.split()[-5:]) == 5 and all(
                    _NUM_GOLDI.fullmatch(n) for n in nums):
                dd, mm, aa = m.groups()
                qt, unit, total, _desc, liq = nums
                if not _br(total):
                    continue  # linha de taxa/servico zerada ('1,000 ... 0,00'), nao e abastecimento
                placa = _PLACA.search(ln)
                out.append({
                    # sem codigo de transacao: fatura + ordem (o mesmo extrato pode
                    # estar anexado a mais de um processo)
                    "transacao": f"goldi-{fatura}-{len(out)}",
                    "data": f"{aa if len(aa) == 4 else '20' + aa}-{mm}-{dd}",
                    "subunidade": depto, "placa": placa.group(0) if placa else None,
                    "combustivel_texto": produto, "combustivel": tipo_combustivel(produto),
                    "estabelecimento": None, "cidade": None, "uf": None, "cnpj_posto": None,
                    "litros": _br(qt), "preco_litro": _br(unit), "valor_bruto": _br(total), "valor_liquido": _br(liq),
                    "km_rodado": None, "km_por_litro": None,
                })
    return out
