import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "relatorios"))
from gerar_relatorio_anual import Doc, evidencia, html_doc, num  # noqa: E402


def test_num_inteiro_sem_casas():
    assert num(34.0) == "34"
    assert num(3.2389) == "3,24"
    assert num(635437.9, "R$") == "R$ 635.438"
    assert num(None) == "—"


def test_evidencia_sem_nome_interno():
    assert evidencia("consumo_m3: último mês com dado 07/2026") == "dados do painel: último mês com dado 07/2026"
    assert evidencia("empenhado_itens (Lâmpadas LED): último mês") == "Lâmpadas LED: último mês"


def test_html_numera_secoes_e_tabelas():
    doc = Doc()
    doc.h1("Apresentação")
    doc.pendente("Composição da Comissão")
    doc.tabela("Faixas", ["A", "B"], [["x", 1]], num={1})
    doc.h1("Anexo A", anexo=True)
    doc.passos(["baixar `pls_despesas`", "somar"])
    doc.ficha([("Fórmula", "a / b"), ("Meta", "")])
    meta = {k: "x" for k in ("titulo", "eyebrow", "h1", "lead", "selo")} | {"rodape_html": "r"}
    out = html_doc(doc, meta)
    assert "1. Apresentação" in out and "Tabela 1 – Faixas" in out
    assert "A preencher pela Comissão" in out and '<td class="n">1</td>' in out
    assert "<ol><li>baixar <code>pls_despesas</code></li>" in out
    assert "<dt>Fórmula</dt>" in out and "<dt>Meta</dt>" not in out
    assert "{{" not in out
