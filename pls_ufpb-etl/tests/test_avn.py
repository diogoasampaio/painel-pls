import pandas as pd
import pytest

from common import config
from common.storage import save_processed
from compras.avn import ler_pedidos
from compras.quantidades import avn_quantidades, unidades_no_nome

# trecho do texto de um ATESTADO do SIPAC (pedido do BRS Supply Manager), sem os dados pessoais
ATESTADO = """ATESTO DE NOTA FISCAL Número do Pedido AVN:6596442
Número do Pedido
6596442
Entregue
Data do Pedido
26/11/2024 13:50:37
Local de Entrega
CCEN - Almoxarifado Setorial
BRS - Supply Manager
Caneta Esferográfica Compactor Economic 1.0mm Azul
Escritório e Papelaria|Canetas e Marcadores|Caneta Esferográfica
Cód: 029618||

NCM: 96081000
- Br Supply - CD São Leopoldo
Quant
300
R$ 0,55
R$ 165,00
Papel Sulfite A4 Chamex 75g 210x297mm 500 Folhas
Escritório e Papelaria|Papéis|Papel Sulfite
Cód: 000123||

NCM: 48025610
- Br Supply - CD São Leopoldo
Quant
1.200
R$ 22,10
R$ 26.520,00
Valor Total:
R$ 26.685,00
"""


def test_le_itens_do_pedido_sem_dado_pessoal():
    p = ler_pedidos(ATESTADO)
    assert [x["codigo"] for x in p] == ["029618", "000123"]
    assert p[1]["quantidade"] == 1200 and p[1]["valor"] == 26520.0
    assert p[0]["pedido"] == "6596442" and p[0]["data_pedido"] == "26/11/2024"
    assert p[0]["setor_entrega"] == "CCEN - Almoxarifado Setorial"
    assert sum(x["valor"] for x in p) == pytest.approx(p[0]["total_pedido"])
    assert not any(k in p[0] for k in ("solicitante", "email", "aprovador", "recebedor"))


@pytest.mark.parametrize("produto, familia, esperado", [
    ("Copo Descartável 180ml PP Branco PCT 100UN", "copo", (100, False)),
    ("Copo Plástico 50ml", "copo", (100, True)),  # sem embalagem no nome: pacote presumido
    ("Papel Sulfite A4 Chamex 75g 500 Folhas", "papel", (1, False)),
    ("Papel A4 Report Caixa 10 Resmas", "papel", (10, False)),
    ("Cartucho Epson T664 Kit 4UN", "toner", (4, False)),
])
def test_unidades_no_nome_do_produto(produto, familia, esperado):
    assert unidades_no_nome(produto, familia) == esperado


def test_pedidos_do_avn_entram_como_aquisicao(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "PROCESSED_DIR", tmp_path)
    df = pd.DataFrame(ler_pedidos(ATESTADO)).assign(periodo="2024-11", ano=2024, mes=11, processo="002508/2025-45")
    save_processed(df, "pls_avn_itens")
    q = avn_quantidades()
    assert list(q["familia"]) == ["papel"]  # caneta nao e copo, papel nem toner
    assert q.iloc[0]["quantidade"] == 1200 and q.iloc[0]["metodo"] == "avn" and q.iloc[0]["periodo"] == "2024-11"


# layout de 2026: data e total na mesma linha do rotulo, espacos no fim e categoria quebrada em duas linhas
ATESTADO_2026 = """Número do Pedido
8774804
Situação
Entregue
Detalhes do Pedido
Data do Pedido 02/03/2026 12:42:53
Local de Entrega Centro de Ciências Sociais Aplicadas - CCSA
Itens do Pedido
Porta Caneta Triplo Cristal 
Escritório e Papelaria | Organização | Porta Lápis e Canetas 
Cód: 049651 | |  
Br Supply - CD São Leopoldo 
Ordem: | Sequência:
Quant 
3
R$ 10,50 
R$ 31,50
Cola Instantânea Loctite Super Bonder 5g 
Limpeza e Manutenção | Autoadesivos e Colas | Cola 
Instantânea/Isopor/Silico 
Cód: 011280 | |  
Br Supply - CD São Leopoldo 
Ordem: | Sequência:
Quant 
4
R$ 5,99 
R$ 23,96
SubTotal: R$ 55,46
Valor Total: R$ 55,46
"""


def test_layout_2026_com_categoria_quebrada():
    p = ler_pedidos(ATESTADO_2026)
    assert [x["produto"] for x in p] == ["Porta Caneta Triplo Cristal", "Cola Instantânea Loctite Super Bonder 5g"]
    assert p[1]["categoria"].endswith("Cola Instantânea/Isopor/Silico")
    assert p[0]["data_pedido"] == "02/03/2026" and p[0]["setor_entrega"].startswith("Centro de Ciências Sociais")
    assert sum(x["valor"] for x in p) == pytest.approx(p[0]["total_pedido"]) == 55.46


def test_pedido_cancelado_fica_fora():
    assert ler_pedidos(ATESTADO_2026.replace("Situação\nEntregue", "Situação\nCancelado")) == []


def test_item_com_desconto_tem_tres_valores():
    # preco de tabela, unitario com desconto e total: vale o ultimo como total
    txt = ATESTADO_2026.replace("Quant \n3\nR$ 10,50 \nR$ 31,50", "Quant \n3\nR$ 70,94 \nR$ 10,50 \nR$ 31,50")
    p = ler_pedidos(txt)
    assert p[0]["preco"] == 10.50 and p[0]["valor"] == 31.50
    assert sum(x["valor"] for x in p) == pytest.approx(55.46)


def test_adesao_ao_avn_pelas_ugs_que_pagaram_no_ano(tmp_path, monkeypatch):
    from indicadores.build_indicadores import _adesao_avn

    monkeypatch.setattr(config, "PROCESSED_DIR", tmp_path)
    monkeypatch.setattr(config, "UGS", ["153065", "153066", "153073", "153074"])
    save_processed(pd.DataFrame({
        "fase": "pagamento", "ano": [2025, 2025, 2025, 2025], "periodo": ["2025-03", "2025-11", "2025-12", "2025-12"],
        "ug": ["153065", "153066", "153065", "153073"],
        "favorecido_codigo": ["03746938001387", "09216620000137", "03746938001387", "11111111000111"],
    }), "pls_despesas")
    r = _adesao_avn().iloc[0]
    assert r["valor"] == 50.0 and r["periodo"] == "2025-12"  # 153065 e 153066 de 4 UGs
