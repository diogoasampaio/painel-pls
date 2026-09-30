"""Blocos de relatorio (titulo, paragrafo, tabela, pendencia...) e os dois
desenhos: HTML (pagina web) e Word (python-docx). Os geradores de relatorio
montam o conteudo uma vez em `Doc` e chamam `html_doc` e `docx_doc`."""

from __future__ import annotations

import html
import math
import re
from pathlib import Path

import pandas as pd

FAIXA_ROT = {"atingida": "Meta atingida", "proxima": "Próxima da meta", "progresso": "Em progresso",
             "distante": "Distante da meta", "nao_avaliavel": "Não avaliável", "sem_dado": "Sem dado",
             "sem_meta": "Sem meta"}
# fundo das celulas de faixa no Word (hex sem #) e classe no HTML
FAIXA_COR = {"atingida": "D6EDE2", "proxima": "E4EFD6", "progresso": "F8EACD", "distante": "F6D9D6",
             "nao_avaliavel": "DDE6EF", "sem_dado": "E6E9EC", "sem_meta": "F0F2F4"}


# ------------------------------------------------------------------ formatos

def vazio(v) -> bool:
    return v is None or (isinstance(v, float) and math.isnan(v)) or v is pd.NA


def num(v, unidade: str = "") -> str:
    if vazio(v):
        return "—"
    v = float(v)
    casas = 0 if abs(v) >= 100 or v.is_integer() else (1 if abs(v) >= 10 else 2)
    s = f"{v:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {s}" if unidade == "R$" else s


def pct(v, casas: int = 1) -> str:
    return "—" if vazio(v) else f"{float(v):.{casas}f}%".replace(".", ",")


def mi(v) -> str:
    return "—" if vazio(v) else "R$ " + f"{v / 1e6:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".") + " mi"


def data_br(d) -> str:
    return pd.Timestamp(d).strftime("%d/%m/%Y")


# ------------------------------------------------------------------ conteudo

class Doc:
    """Lista de blocos com numeracao de secoes e tabelas."""

    def __init__(self):
        self.blocos: list[dict] = []
        self.n_tab = 0
        self.n_sec = 0

    def h1(self, txt, anexo=False, id=None, quebra=False):
        """secao; anexo=True nao numera; quebra=True comeca pagina nova no Word"""
        if not anexo:
            self.n_sec += 1
            txt = f"{self.n_sec}. {txt}"
        n = len([b for b in self.blocos if b["t"] == "h1"]) + 1
        self.blocos.append({"t": "h1", "txt": txt, "id": id or f"s{n}", "quebra": quebra})

    def h2(self, txt):
        self.blocos.append({"t": "h2", "txt": txt})

    def h3(self, txt):
        self.blocos.append({"t": "h3", "txt": txt})

    def passos(self, itens):
        if itens:
            self.blocos.append({"t": "passos", "itens": list(itens)})

    def ficha(self, pares):
        """quadro rotulo -> valor"""
        self.blocos.append({"t": "ficha", "pares": [(k, v) for k, v in pares if v]})

    def p(self, txt):
        self.blocos.append({"t": "p", "txt": txt})

    def nota(self, txt):
        self.blocos.append({"t": "nota", "txt": txt})

    def pendente(self, txt):
        self.blocos.append({"t": "pendente", "txt": txt})

    def lista(self, itens):
        if itens:
            self.blocos.append({"t": "lista", "itens": list(itens)})

    def kpis(self, itens):
        self.blocos.append({"t": "kpis", "itens": itens})

    def faixas(self, contagem: list[tuple[str, int]]):
        self.blocos.append({"t": "faixas", "itens": [(c, n) for c, n in contagem if n]})

    def tabela(self, titulo, cab, linhas, num=(), larg=None, fonte=""):
        self.n_tab += 1
        self.blocos.append({"t": "tabela", "titulo": f"Tabela {self.n_tab} – {titulo}", "cab": cab, "linhas": linhas,
                            "num": set(num), "larg": larg or [1] * len(cab), "fonte": fonte})


def fx(codigo) -> dict:
    """celula de faixa: texto + cor"""
    codigo = codigo if isinstance(codigo, str) and codigo else "sem_meta"
    return {"txt": FAIXA_ROT.get(codigo, codigo), "fx": codigo}



# ------------------------------------------------------------------ HTML

e = html.escape


def md(txt) -> str:
    """**negrito**, `codigo` e links soltos"""
    s = e(str(txt))
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"`(.+?)`", r"<code>\1</code>", s)
    return re.sub(r"(https://[^\s<]+[^\s<.,;)])", r'<a href="\1" target="_blank" rel="noopener">\1</a>', s)


def celula_html(c, numerica: bool) -> str:
    if isinstance(c, dict):
        return f'<td><span class="fx fx-{c["fx"]}">{e(c["txt"])}</span></td>'
    cls = ' class="n"' if numerica else ""
    return f"<td{cls}>{md(c)}</td>"


def html_doc(doc: Doc, meta: dict) -> str:
    corpo, toc = [], []
    for b in doc.blocos:
        t = b["t"]
        if t == "h1":
            if corpo:
                corpo.append("</section>")
            toc.append(f'<li><a href="#{b["id"]}">{e(b["txt"])}</a></li>')
            corpo.append(f'<section id="{e(b["id"])}"><h2>{e(b["txt"])}</h2>')
        elif t == "h2":
            corpo.append(f"<h3>{e(b['txt'])}</h3>")
        elif t == "h3":
            corpo.append(f"<h4>{e(b['txt'])}</h4>")
        elif t == "passos":
            corpo.append("<ol>" + "".join(f"<li>{md(i)}</li>" for i in b["itens"]) + "</ol>")
        elif t == "ficha":
            corpo.append('<dl class="ficha">' + "".join(f"<div><dt>{e(k)}</dt><dd>{md(v)}</dd></div>"
                                                        for k, v in b["pares"]) + "</dl>")
        elif t == "p":
            corpo.append(f"<p>{md(b['txt'])}</p>")
        elif t == "nota":
            corpo.append(f'<p class="nota">{md(b["txt"])}</p>')
        elif t == "pendente":
            corpo.append(f'<aside class="pend"><b>A preencher pela Comissão</b><p>{md(b["txt"])}</p></aside>')
        elif t == "lista":
            corpo.append("<ul>" + "".join(f"<li>{md(i)}</li>" for i in b["itens"]) + "</ul>")
        elif t == "kpis":
            corpo.append('<div class="kpis">' + "".join(f'<div class="kpi"><b>{e(v)}</b><span>{e(r)}</span></div>'
                                                        for v, r in b["itens"]) + "</div>")
        elif t == "faixas":
            tot = sum(n for _, n in b["itens"]) or 1
            segs = "".join(f'<span class="seg fxb-{c}" style="flex:{n}" title="{e(FAIXA_ROT[c])}: {n}">{n}</span>'
                           for c, n in b["itens"])
            leg = "".join(f'<li><i class="sw fxb-{c}"></i>{e(FAIXA_ROT[c])} <b>{n}</b></li>' for c, n in b["itens"])
            corpo.append(f'<figure class="faixas"><figcaption>Indicadores do núcleo por faixa ({tot})</figcaption>'
                         f'<div class="barra">{segs}</div><ul class="leg">{leg}</ul></figure>')
        elif t == "tabela":
            cab = "".join(f'<th{" class=n" if i in b["num"] else ""}>{e(h)}</th>' for i, h in enumerate(b["cab"]))
            linhas = "".join("<tr>" + "".join(celula_html(c, i in b["num"]) for i, c in enumerate(l)) + "</tr>"
                             for l in b["linhas"])
            fonte = f'<p class="fonte">Fonte: {md(b["fonte"])}</p>' if b["fonte"] else ""
            corpo.append(f'<figure class="tab"><figcaption>{e(b["titulo"])}</figcaption><div class="rolar"><table>'
                         f"<thead><tr>{cab}</tr></thead><tbody>{linhas}</tbody></table></div>{fonte}</figure>")
    corpo.append("</section>")
    tpl = Path(__file__).with_name("relatorio_template.html").read_text(encoding="utf-8")
    out = tpl.replace("{{TOC}}", "".join(toc)).replace("{{CORPO}}", "".join(corpo))
    for k in ("titulo", "eyebrow", "h1", "lead", "selo"):
        out = out.replace("{{" + k.upper() + "}}", e(meta[k]))
    return out.replace("{{RODAPE}}", meta["rodape_html"])


# ------------------------------------------------------------------ Word

def docx_doc(doc: Doc, meta: dict, destino: Path) -> None:
    from docx import Document
    from docx.enum.section import WD_ORIENT  # noqa: F401
    from docx.enum.table import WD_TABLE_ALIGNMENT
    from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Cm, Pt, RGBColor

    AZUL = RGBColor(0x0B, 0x4F, 0x8A)
    TINTA = RGBColor(0x10, 0x26, 0x3D)
    CINZA = RGBColor(0x4A, 0x5D, 0x70)

    def sombrear(el, cor):
        pr = el.get_or_add_tcPr() if hasattr(el, "get_or_add_tcPr") else el.get_or_add_pPr()
        shd = OxmlElement("w:shd")
        shd.set(qn("w:val"), "clear")
        shd.set(qn("w:color"), "auto")
        shd.set(qn("w:fill"), cor)
        pr.append(shd)

    def borda_paragrafo(p, cor="E0A24A", lado="left", tam="18"):
        pPr = p._p.get_or_add_pPr()
        bdr = OxmlElement("w:pBdr")
        b = OxmlElement(f"w:{lado}")
        for k, v in (("val", "single"), ("sz", tam), ("space", "8"), ("color", cor)):
            b.set(qn(f"w:{k}"), v)
        bdr.append(b)
        pPr.append(bdr)

    def campo(p, instr):
        r = p.add_run()
        for tipo, txt in (("begin", None), (None, instr), ("separate", None), ("end", None)):
            if tipo:
                fc = OxmlElement("w:fldChar")
                fc.set(qn("w:fldCharType"), tipo)
                if tipo == "begin" and instr.startswith("TOC"):
                    fc.set(qn("w:dirty"), "true")  # Word monta o sumario ao abrir
                r._r.append(fc)
            else:
                it = OxmlElement("w:instrText")
                it.set(qn("xml:space"), "preserve")
                it.text = txt
                r._r.append(it)

    def texto(p, txt, tam=None, cor=None):
        for i, parte in enumerate(re.split(r"\*\*(.+?)\*\*", str(txt))):
            for j, trecho in enumerate(re.split(r"`(.+?)`", parte)):
                if not trecho:
                    continue
                run = p.add_run(trecho)
                run.bold = i % 2 == 1 or None
                if j % 2 == 1:  # `codigo`
                    run.font.name = "Consolas"
                    run.font.size = Pt((tam or 11) - 1)
                elif tam:
                    run.font.size = Pt(tam)
                if cor:
                    run.font.color.rgb = cor

    w = Document()
    sec = w.sections[0]
    sec.page_height, sec.page_width = Cm(29.7), Cm(21)
    sec.left_margin = sec.right_margin = Cm(2.5)
    sec.top_margin, sec.bottom_margin = Cm(2.2), Cm(2)
    larg_util = 16.0  # cm
    if meta.get("paisagem"):  # tabelas largas (muitas colunas de texto)
        from docx.enum.section import WD_ORIENT
        sec.orientation = WD_ORIENT.LANDSCAPE
        sec.page_height, sec.page_width = Cm(21), Cm(29.7)
        sec.left_margin = sec.right_margin = Cm(2)
        larg_util = 25.7

    est = w.styles
    est["Normal"].font.name = "Calibri"
    est["Normal"].font.size = Pt(11)
    est["Normal"].font.color.rgb = TINTA
    est["Normal"].paragraph_format.space_after = Pt(6)
    est["Normal"].paragraph_format.line_spacing = 1.15
    for nome, tam, antes in (("Title", 24, 0), ("Heading 1", 15, 18), ("Heading 2", 12.5, 12),
                              ("Heading 3", 11, 8)):
        s = est[nome]
        s.font.name = "Calibri"
        s.font.size = Pt(tam)
        s.font.bold = True
        s.font.color.rgb = AZUL if nome != "Title" else TINTA
        s.paragraph_format.space_before = Pt(antes)
        s.paragraph_format.space_after = Pt(6)
        s.paragraph_format.keep_with_next = True

    # rodape: pagina
    pr = sec.footer.paragraphs[0]
    pr.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    texto(pr, f"{meta['rodape_doc']} · página ", 8.5, CINZA)
    campo(pr, "PAGE")

    # capa
    p = w.add_paragraph()
    p.paragraph_format.space_before = Pt(120)
    texto(p, "UNIVERSIDADE FEDERAL DA PARAÍBA", 11, AZUL)
    texto(w.add_paragraph(), "Comissão Gestora do Plano de Logística Sustentável", 11, CINZA)
    t = w.add_paragraph(style="Title")
    t.paragraph_format.space_before = Pt(36)
    t.add_run(meta["h1"])
    texto(w.add_paragraph(), meta["subtitulo"], 16, AZUL)
    p = w.add_paragraph()
    p.paragraph_format.space_before = Pt(36)
    texto(p, meta["nota_capa"], 10, CINZA)
    w.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
    w.add_paragraph("Sumário", style="Heading 1")
    p = w.add_paragraph()
    campo(p, f'TOC \\o "1-{meta.get("toc_niveis", 2)}" \\h \\z \\u')
    texto(w.add_paragraph(), "Para atualizar o sumário no Word: clique com o botão direito sobre ele e escolha "
                             "“Atualizar campo”.", 9, CINZA)
    w.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

    for b in doc.blocos:
        tp = b["t"]
        if tp == "h1":
            h = w.add_paragraph(b["txt"], style="Heading 1")
            h.paragraph_format.page_break_before = bool(b.get("quebra"))
        elif tp == "h2":
            w.add_paragraph(b["txt"], style="Heading 2")
        elif tp == "h3":
            w.add_paragraph(b["txt"], style="Heading 3")
        elif tp == "passos":
            for n, i in enumerate(b["itens"], 1):
                p = w.add_paragraph()
                p.paragraph_format.left_indent = Cm(0.8)
                p.paragraph_format.first_line_indent = Cm(-0.6)
                p.paragraph_format.tab_stops.add_tab_stop(Cm(0.8))
                texto(p, f"{n}.\t{i}")
        elif tp == "ficha":
            tb = w.add_table(rows=0, cols=2)
            tb.style = "Table Grid"
            for k, v in b["pares"]:
                c1, c2 = tb.add_row().cells
                c1.width, c2.width = Cm(4), Cm(larg_util - 4)
                sombrear(c1._tc, "E3EEF8")
                for c in (c1, c2):
                    c.paragraphs[0].paragraph_format.space_after = Pt(0)
                texto(c1.paragraphs[0], f"**{k}**", 9.5)
                texto(c2.paragraphs[0], v, 9.5)
            w.add_paragraph().paragraph_format.space_after = Pt(2)
        elif tp == "p":
            texto(w.add_paragraph(), b["txt"])
        elif tp == "nota":
            texto(w.add_paragraph(), b["txt"], 9, CINZA)
        elif tp == "pendente":
            p = w.add_paragraph()
            sombrear(p._p, "FFF2CC")
            borda_paragrafo(p)
            texto(p, "A preencher pela Comissão: ", None, RGBColor(0x8A, 0x55, 0x00))
            p.runs[-1].bold = True
            texto(p, b["txt"])
        elif tp == "lista":
            for i in b["itens"]:
                p = w.add_paragraph(style="List Bullet")
                p.paragraph_format.space_after = Pt(3)
                texto(p, i)
        elif tp in ("kpis", "faixas"):
            itens = b["itens"] if tp == "kpis" else [(str(n), FAIXA_ROT[c]) for c, n in b["itens"]]
            tb = w.add_table(rows=2, cols=len(itens))
            tb.alignment = WD_TABLE_ALIGNMENT.CENTER
            for j, (v, r) in enumerate(itens):
                c1, c2 = tb.cell(0, j), tb.cell(1, j)
                for c in (c1, c2):
                    c.width = Cm(larg_util / len(itens))
                    if tp == "faixas":
                        sombrear(c._tc, FAIXA_COR[b["itens"][j][0]])
                c1.paragraphs[0].alignment = c2.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
                texto(c1.paragraphs[0], f"**{v}**", 18 if tp == "kpis" else 14, AZUL if tp == "kpis" else TINTA)
                texto(c2.paragraphs[0], r, 9, CINZA)
            w.add_paragraph()
        elif tp == "tabela":
            cap = w.add_paragraph()
            cap.paragraph_format.keep_with_next = True
            cap.paragraph_format.space_before = Pt(8)
            texto(cap, f"**{b['titulo']}**", 9.5, TINTA)
            tb = w.add_table(rows=1, cols=len(b["cab"]))
            tb.style = "Table Grid"
            tb.autofit = False  # respeita as larguras (URL longa nao alarga a coluna)
            tot = sum(b["larg"])
            larg = [Cm(larg_util * x / tot) for x in b["larg"]]
            for j, h in enumerate(b["cab"]):
                c = tb.rows[0].cells[j]
                c.width = larg[j]
                sombrear(c._tc, "0B4F8A")
                texto(c.paragraphs[0], f"**{h}**", 9, RGBColor(0xFF, 0xFF, 0xFF))
            trPr = tb.rows[0]._tr.get_or_add_trPr()
            th = OxmlElement("w:tblHeader")
            th.set(qn("w:val"), "true")
            trPr.append(th)
            for linha in b["linhas"]:
                cels = tb.add_row().cells
                for j, v in enumerate(linha):
                    c = cels[j]
                    c.width = larg[j]
                    par = c.paragraphs[0]
                    par.paragraph_format.space_after = Pt(0)
                    if isinstance(v, dict):
                        sombrear(c._tc, FAIXA_COR.get(v["fx"], "FFFFFF"))
                        v = v["txt"]
                    if j in b["num"]:
                        par.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                    texto(par, v, 9)
            if b["fonte"]:
                texto(w.add_paragraph(), f"Fonte: {b['fonte']}", 8.5, CINZA)
            else:
                w.add_paragraph().paragraph_format.space_after = Pt(2)
    w.core_properties.title = meta["titulo"]
    w.core_properties.author = "Painel de Sustentabilidade da UFPB"
    w.save(destino)

