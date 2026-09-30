"""Pedidos do Almoxarifado Virtual Nacional (AVN) atestados nos processos de pagamento -> pls_avn_itens.

O AVN (Central de Compras, operado na regiao pela BRS Suprimentos Corporativos)
e empenhado como servico (3.3.90.39-84): o Portal so traz o valor. O que foi
pedido esta no SIPAC: cada processo de pagamento da nota fiscal mensal tem um
ATESTADO por unidade, e cada atestado anexa o pedido do sistema BRS Supply
Manager com uma linha por produto (nome, categoria, codigo, NCM, quantidade,
preco, total).

  processos  os citados nos pagamentos ao operador (observacao "PROC. ...") mais os
             da base aberta de processos da UFPB com assunto de pagamento de nota
             fiscal ao operador (CNPJs em ref/avn_operadores.csv)
  leitura    documentos ATESTADO (2024 em diante) e DOCUMENTO COMPROBATORIO (2022-2023, o pedido
             ia como anexo); o PDF e apagado depois de lido. Pedido cancelado fica fora
  LGPD       solicitante, aprovador, recebedor, e-mail e telefone do pedido sao
             descartados: fica so o setor de entrega (unidade), produto e valores

Um pedido pode aparecer em mais de um processo (reatesto): vale uma vez, pela
chave numero do pedido + codigo do produto. O periodo e o mes do pedido: o
indicador mede aquisicao, nao consumo.

Cache: data/raw/sipac/avn/<processo>.json (pedidos ja lidos, sem dado pessoal).
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from common import config
from common.mongo import replace_by
from common.storage import load_processed, raw_path, read_json, save_processed, write_json
from common.validation import report_counts

COLLECTION = "pls_avn_itens"


def operadores() -> set[str]:
    arq = config.REF_DIR / "avn_operadores.csv"
    return set(pd.read_csv(arq, sep=";", dtype=str)["cnpj"]) if arq.exists() else set()


def _num(txt: str) -> float:
    return float(txt.replace(".", "").replace(",", "."))


# item do pedido no texto extraido do PDF. Tres layouts do BRS Supply Manager: 2022-2023 (sem NCM),
# 2024-2025 (com NCM) e 2026 (rotulo e valor na mesma linha, espacos no fim das linhas):
#   <produto>\n<categoria com |>\nCód: 029618||\n \nNCM: 96081000\n- Br Supply - CD ...\nQuant\n300\nR$ 0,55\nR$ 165,00
# ancora no "Cód:": produto e categoria sao as linhas logo acima (a categoria pode quebrar em duas)
# depois da quantidade vem 2 valores (unitario, total) ou 3 com desconto (preco de tabela, unitario, total):
# vale sempre o ultimo como total e o penultimo como unitario
ITEM = re.compile(
    r"C[óo]d:\s*(\d+)[^\n]*\n((?:(?!Quant\s*\n)[^\n]*\n){0,4}?)"
    r"Quant\s*\n([\d.,]+)\s*\n((?:R\$\s*[\d.,]+\s*(?:\n|$))+)")
VALOR = re.compile(r"R\$\s*([\d.,]+)")
NCM = re.compile(r"NCM:\s*(\d+)")
PEDIDO = re.compile(r"N[úu]mero do Pedido\s*\n(\d+)")
DATA = re.compile(r"Data do Pedido\s+(\d{2}/\d{2}/\d{4})")
LOCAL = re.compile(r"Local de Entrega(?:[ \t]+|\n)(?!Nome / Raz)([^\n]+)")
SITUACAO = re.compile(r"Situa[çc][ãa]o\s*\n([^\n]+)")
TOTAL = re.compile(r"Valor Total:\s*R\$\s*([\d.,]+)")
CANCELADO = re.compile(r"cancel", re.I)
# documentos do processo que trazem o pedido: o atestado (2024 em diante) ou um anexo (2022-2023)
ESPECIES = ("ATESTADO", "DOCUMENTO COMPROBAT")


def _produto_categoria(cabeca: str) -> tuple[str, str]:
    """Linhas entre o item anterior e o "Cód:": o produto e a linha antes da 1a linha com '|'
    (categoria), e a categoria vai ate o fim (pode quebrar em duas linhas)."""
    linhas = [l.strip() for l in cabeca.split("\n") if l.strip()]
    c = next((k for k, l in enumerate(linhas) if "|" in l), None)
    if c is None or c == 0:
        return (linhas[-1] if linhas else ""), ""
    return linhas[c - 1], " ".join(linhas[c:])


def _itens(bloco: str) -> list[tuple]:
    out, fim = [], 0
    for m in ITEM.finditer(bloco):
        produto, categoria = _produto_categoria(bloco[fim:m.start()])
        valores = VALOR.findall(m.group(4))
        if len(valores) >= 2:
            out.append((produto, categoria, m.group(1), m.group(2), m.group(3), valores[-2], valores[-1]))
        fim = m.end()
    return out


def ler_pedidos(texto: str) -> list[dict]:
    """Pedidos (um ou mais) do texto de um ATESTADO. So produto, setor de entrega e valores."""
    out = []
    inicios = [m.start() for m in PEDIDO.finditer(texto)]
    # o numero do pedido aparece no cabecalho do atestado e no pedido: blocos a partir de cada ocorrencia
    blocos = [texto[a:b] for a, b in zip(inicios, [*inicios[1:], len(texto)])] or [texto]
    vistos = set()
    for bloco in blocos:
        p = PEDIDO.search(bloco)
        itens = _itens(bloco)
        if not p or not itens or p.group(1) in vistos:
            continue
        vistos.add(p.group(1))
        d, local, total = DATA.search(bloco), LOCAL.search(bloco), TOTAL.search(bloco)
        sit = SITUACAO.search(bloco)
        if sit and CANCELADO.search(sit.group(1)):
            continue
        for produto, categoria, codigo, meio, qtd, preco, valor in itens:
            ncm = NCM.search(meio)
            out.append({"pedido": p.group(1), "data_pedido": d.group(1) if d else None,
                        "setor_entrega": local.group(1).strip() if local else None,
                        "situacao_pedido": sit.group(1).strip() if sit else None,
                        "produto": produto.strip(), "categoria": categoria.strip(), "codigo": codigo,
                        "ncm": ncm.group(1) if ncm else None,
                        "quantidade": _num(qtd), "preco": _num(preco), "valor": _num(valor),
                        "total_pedido": _num(total.group(1)) if total else None})
    return out


def _texto_pdf(pdf: Path) -> str:
    import pypdf

    return "\n".join(p.extract_text() or "" for p in pypdf.PdfReader(str(pdf)).pages)


# ------------------------------------------------------------------ processos

def processos() -> pd.DataFrame:
    """Processos de pagamento ao operador do AVN: dos pagamentos (Portal) e da base aberta de processos."""
    from faturas.load_faturas import normalizar_processo

    cnpjs = operadores()
    d = load_processed("pls_despesas")
    pg = d[(d["fase"] == "pagamento") & d["favorecido_codigo"].isin(cnpjs)] if not d.empty else d
    lista = {p for p in pg["observacao"].map(normalizar_processo) if p} if not pg.empty else set()
    try:
        from faturas.processos_ufpb import base

        b = base(offline=True)
        m = b["assunto_detalhado"].fillna("").str.upper()
        sel = b[m.str.contains("PAGAMENTO") & m.str.contains("BRS SUPRIMENTOS")]
        lista |= set(sel["processo"])
    except Exception as e:  # base de processos indisponivel: fica so o que os pagamentos citam
        print(f"  AVN: base de processos indisponível ({type(e).__name__})")
    from faturas.processos_ufpb import valido

    # o extrator de numero de processo tambem casa pedacos de CNPJ ("620/0001-37"): so vale DV correto
    return pd.DataFrame({"processo": sorted(x for x in lista if valido(x))})


def _ler_processo(sip, processo: str) -> dict:
    cache = raw_path("sipac", "avn", f"{processo.replace('/', '_')}.json")
    if cache.exists():
        dados = read_json(cache)
        # sem pedido legivel: le de novo (o leitor pode ter aprendido um formato novo)
        if dados.get("status") != "sem_pedido_legivel":
            return dados
    achou = sip.buscar(processo)
    if not achou:
        dados = {"processo": processo, "status": "processo_nao_encontrado", "pedidos": []}
    else:
        pedidos = []
        for doc in sip.documentos(achou["id"]):
            if not doc["arquivo"] or not doc["especie"].upper().startswith(ESPECIES):
                continue
            pdf = raw_path("sipac", "pdf", f"avn_{processo.replace('/', '_')}_{doc['ordem']}.pdf")
            try:
                sip.baixar(doc["arquivo"], pdf)
                pedidos += ler_pedidos(_texto_pdf(pdf))
            except Exception as e:
                print(f"  AVN {processo} doc {doc['ordem']}: {type(e).__name__}: {e}", flush=True)
            finally:
                if pdf.exists() and not config.SIPAC_GUARDAR_PDF:
                    pdf.unlink()
        dados = {"processo": processo, "assunto": achou["assunto"], "status": "ok" if pedidos else "sem_pedido_legivel",
                 "pedidos": pedidos}
    write_json(cache, dados)
    return dados


def extrair() -> pd.DataFrame:
    from faturas.sipac import Sipac

    procs = processos()
    sip = Sipac()
    linhas, status = [], {}
    for k, p in enumerate(procs["processo"], 1):
        dados = _ler_processo(sip, p)
        status[dados["status"]] = status.get(dados["status"], 0) + 1
        linhas += [{**x, "processo": p} for x in dados["pedidos"]]
        if k % 20 == 0:
            print(f"  AVN: {k}/{len(procs)} processos", flush=True)
    report_counts("AVN - processos por situação", status)
    df = pd.DataFrame(linhas)
    if df.empty:
        return df
    # reatesto do mesmo pedido em outro processo; o mesmo produto pode vir em duas linhas do pedido
    df = df.drop_duplicates(["pedido", "codigo", "quantidade", "valor"])
    # conferencia: soma dos itens lidos x valor total impresso no pedido
    conf = df.groupby("pedido").agg(soma=("valor", "sum"), total=("total_pedido", "first"))
    difere = conf[conf["total"].notna() & ((conf["soma"] - conf["total"]).abs() > 0.05)]
    report_counts("AVN - pedidos com soma dos itens = total impresso",
                  {"confere": len(conf) - len(difere), "difere": len(difere)})
    dt = pd.to_datetime(df["data_pedido"], format="%d/%m/%Y", errors="coerce")
    return df.assign(periodo=dt.dt.strftime("%Y-%m"), ano=dt.dt.year.astype("Int64"), mes=dt.dt.month.astype("Int64"))


def run(*, dry_run: bool = False, **_: object) -> None:
    if not operadores():
        print("AVN: sem CNPJ do operador em ref/avn_operadores.csv")
        return
    df = extrair()
    if df.empty:
        print("AVN: nenhum pedido lido")
        return
    report_counts("AVN - pedidos por ano", df.groupby("ano")["pedido"].nunique().to_dict())
    report_counts("AVN - valor dos itens por ano (R$)", df.groupby("ano")["valor"].sum().round(2).to_dict())
    if not dry_run:
        save_processed(df, COLLECTION)
    replace_by(COLLECTION, df, "ano", dry_run=dry_run)


if __name__ == "__main__":
    run()
