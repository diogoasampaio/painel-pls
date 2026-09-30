"""Texto dos documentos das contratacoes (PNCP) e marcadores do PLS.

Extracao: PDF (pypdfium2, rapido mesmo com 100+ paginas), ZIP (le cada
arquivo de dentro), DOCX/ODT (XML do pacote), HTML/TXT. PDF escaneado sai sem
texto e a contratacao fica `sem_texto`.

Paginas: o Compras.gov.br gera ETP, TR e edital com cabecalho em toda pagina
("UASG 153065 Termo de Referencia 41/2024", "... Estudo Tecnico Preliminar
7/2024"), e a UFPB costuma publicar os tres num unico PDF. Cada pagina recebe
o tipo pelo cabecalho; sem cabecalho, herda o tipo do documento no PNCP.

Regras (ref/criterios_editais.csv), sobre texto sem acento e em maiusculas:
  sustentabilidade  especifico  exigencia concreta (logistica reversa, Procel,
                                madeira legal, reciclado, gas refrigerante,
                                cota social...) -- so conta fora do ETP: o ETP
                                estuda impactos, quem obriga e o TR/edital
                    generico    mencao a "criterios de sustentabilidade", IN
                                01/2010, Guia da AGU... em qualquer pagina
  demais marcadores criterio    presenca do termo em qualquer pagina fora do ETP
                                (mao de obra exclusiva, cota para mulheres,
                                mao de obra local, alimentos, agricultura
                                familiar, obra de engenharia, BIM)

O modelo de TR da AGU/SEGES traz a secao "Sustentabilidade" ja com o texto
generico ("Alem dos criterios de sustentabilidade eventualmente inseridos...");
por isso so o termo nao basta e o nivel especifico exige um criterio concreto.

Criterio concreto numa frase de preferencia ("que os bens sejam,
PREFERENCIALMENTE, acondicionados em embalagem ... reciclavel", "a contratada
devera PRIORIZAR bens reciclaveis" -- clausulas-padrao dos modelos da AGU e da
SGD) vira o nivel `preferencial`: nao obriga o fornecedor.
"""

from __future__ import annotations

import io
import re
import unicodedata
import zipfile
from functools import lru_cache

import pandas as pd

from common import config

TIPOS_REQUISITO = {"Edital", "Termo de Referência", "Projeto Básico", "Aviso de Contratação Direta", "Anteprojeto",
                   "Projeto Executivo", "Minuta do Contrato", "Contrato"}
TIPO_ESTUDO = "Estudo Técnico Preliminar"
MAX_TRECHOS = 6
_PREFERENCIA = re.compile(r"PREFERENCIALMENTE|PRIORIZA\w*|SEMPRE QUE POSSIVEL|NO QUE COUBER|QUANDO POSSIVEL|PREFERENCIA (A|PARA|POR)")


def normalizar(texto: str) -> str:
    t = unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode().upper()
    return re.sub(r"[ \t]+", " ", t)


@lru_cache
def regras() -> pd.DataFrame:
    df = pd.read_csv(config.REF_DIR / "criterios_editais.csv", sep=";", dtype=str, keep_default_na=False)
    df["regex"] = df["padrao"].map(re.compile)
    return df


# ---------------------------------------------------------------- extracao

def _pdf(conteudo: bytes) -> list[str]:
    import pypdfium2 as pdfium
    doc = pdfium.PdfDocument(conteudo)
    try:
        return [doc[i].get_textpage().get_text_range() for i in range(len(doc))]
    finally:
        doc.close()


def _xml_pacote(conteudo: bytes, membro: str) -> list[str]:
    with zipfile.ZipFile(io.BytesIO(conteudo)) as z:
        xml = z.read(membro).decode("utf-8", "ignore")
    return [re.sub(r"<[^>]+>", " ", re.sub(r"</w:p>|</text:p>", "\n", xml))]


def paginas(conteudo: bytes, nome: str = "") -> list[str]:
    """Texto por pagina (ZIP: paginas de todos os arquivos de dentro, em ordem)."""
    n = nome.lower()
    try:
        if conteudo[:4] == b"%PDF" or n.endswith(".pdf"):
            return _pdf(conteudo)
        if conteudo[:2] == b"PK":
            with zipfile.ZipFile(io.BytesIO(conteudo)) as z:
                nomes = z.namelist()
                if "word/document.xml" in nomes:
                    return _xml_pacote(conteudo, "word/document.xml")
                if "content.xml" in nomes and "mimetype" in nomes:
                    return _xml_pacote(conteudo, "content.xml")
                out: list[str] = []
                for m in sorted(nomes):
                    if not m.endswith("/"):
                        out += paginas(z.read(m), m)
                return out
        if n.endswith((".html", ".htm", ".txt")) or conteudo[:1] == b"<":
            return [re.sub(r"<[^>]+>", " ", conteudo.decode("utf-8", "ignore"))]
    except Exception:  # arquivo corrompido ou formato desconhecido: sem texto
        return []
    return []


_CABECALHO = re.compile(r"UASG \d{6} (ESTUDO TECNICO PRELIMINAR|TERMO DE REFERENCIA|EDITAL|PROJETO BASICO)")


def tipo_pagina(pagina_norm: str, tipo_documento: str) -> str:
    m = _CABECALHO.search(pagina_norm[:600])
    if m:
        return "etp" if m.group(1).startswith("ESTUDO") else "requisito"
    if tipo_documento == TIPO_ESTUDO:
        return "etp"
    return "requisito" if tipo_documento in TIPOS_REQUISITO else "outro"


# ---------------------------------------------------------------- classificacao

def _frase(texto: str, m: re.Match) -> str:
    """Frase (entre pontos, ponto e virgula ou quebra de item) que contem o achado."""
    ini = max(texto.rfind(". ", 0, m.start()), texto.rfind("; ", 0, m.start()), texto.rfind(":\n", 0, m.start()))
    fins = [i for i in (texto.find(". ", m.end()), texto.find("; ", m.end())) if i != -1]
    return texto[ini + 1 if ini >= 0 else 0: min(fins) if fins else len(texto)]


def _trecho(texto: str, m: re.Match) -> str:
    ini, fim = max(0, m.start() - 160), min(len(texto), m.end() + 200)
    return re.sub(r"\s+", " ", texto[ini:fim]).strip()


def classificar(docs: list[tuple[str, list[str]]], objeto: str = "") -> dict:
    """docs: [(tipo do documento no PNCP, [texto de cada pagina])] -> marcadores.

    Regras com onde=objeto (o que se compra: mao de obra exclusiva, alimentos,
    obra) leem so o objeto da contratacao; as demais, os documentos.

    Devolve nivel de sustentabilidade (especifico | generico | nenhum |
    sem_texto), os marcadores presentes, as regras que casaram e trechos
    para conferencia."""
    tab = regras()
    achados: dict[str, set[str]] = {}
    obj = normalizar(objeto)
    for r in tab[tab["onde"] == "objeto"].itertuples():
        if r.regex.search(obj):
            achados.setdefault(f"{r.marcador}:{r.nivel}", set()).add(r.descricao)
    tab = tab[tab["onde"] == "documento"]
    especificos: list[str] = []
    preferenciais: list[str] = []
    trechos: list[str] = []
    tem_texto = False
    for tipo_doc, pags in docs:
        for pag in pags:
            if len(pag.strip()) < 40:
                continue
            tem_texto = True
            norm = normalizar(pag)
            tipo = tipo_pagina(norm, tipo_doc)
            for r in tab.itertuples():
                if r.nivel == "especifico" or r.marcador != "sustentabilidade":
                    if tipo == "etp":
                        continue  # estudo nao obriga
                m = r.regex.search(norm)
                if not m:
                    continue
                chave = f"{r.marcador}:{r.nivel}"
                achados.setdefault(chave, set()).add(r.descricao)
                if r.marcador == "sustentabilidade" and r.nivel == "especifico":
                    # a mesma regra pode casar numa frase de preferencia e noutra obrigatoria
                    obrigatorio = next((x for x in r.regex.finditer(norm) if not _PREFERENCIA.search(_frase(norm, x))), None)
                    if obrigatorio is None:
                        achados["sustentabilidade:especifico"].discard(r.descricao)
                        if not achados["sustentabilidade:especifico"]:
                            del achados["sustentabilidade:especifico"]
                        if r.descricao not in preferenciais:
                            preferenciais.append(r.descricao)
                        continue
                    if r.descricao not in especificos:
                        especificos.append(r.descricao)
                        if len(trechos) < MAX_TRECHOS:
                            trechos.append(_trecho(norm, obrigatorio))
    if not tem_texto:
        nivel = "sem_texto"
    elif especificos:
        nivel = "especifico"
    elif preferenciais:
        nivel = "preferencial"
    elif "sustentabilidade:generico" in achados:
        nivel = "generico"
    else:
        nivel = "nenhum"
    preferenciais = [x for x in preferenciais if x not in especificos]
    marcadores = sorted({k.split(":")[0] for k in achados if not k.startswith("sustentabilidade")})
    return {"nivel_sustentabilidade": nivel, "criterios": especificos, "preferenciais": preferenciais,
            "marcadores": marcadores,
            "genericos": sorted(achados.get("sustentabilidade:generico", set())), "trechos": trechos,
            "tem_texto": tem_texto}
