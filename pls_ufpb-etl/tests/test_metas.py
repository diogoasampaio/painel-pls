import pandas as pd
import pytest

from common import config
from common.storage import save_processed
from metas import catalogo


def test_catalogo_real_e_valido():
    cat = catalogo.carregar()
    plano = cat[cat["id"].str.startswith("E")]
    assert len(plano) == 34
    assert set(plano["eixo_pls"]) == {"1", "2", "3", "4", "5", "6"}


def test_parse_calculo():
    c = catalogo.parse_calculo("ind:metrica=pago,subtema=Diárias|Passagens e locomoção,campo=valor_real")
    assert c["subtemas"] == ["Diárias", "Passagens e locomoção"] and c["tema"] is None
    assert catalogo.parse_calculo("per_capita") == {"tipo": "per_capita"}
    assert catalogo.parse_calculo("") is None
    with pytest.raises(ValueError):
        catalogo.parse_calculo("ind:metrica=pago,campo=valor_errado")


def _meses(anos: dict[int, tuple[int, float]]) -> pd.DataFrame:
    """{ano: (meses com dado, total do ano)} -> linhas mensais de copos descartaveis."""
    linhas = [
        {"ano": a, "mes": m, "metrica": "quantidade_itens", "tema_codigo": "material_consumo",
         "subtema": "Copos descartáveis", "valor_nominal": total / n}
        for a, (n, total) in anos.items() for m in range(1, n + 1)
    ]
    # cobertura das despesas (os itens so contam o ano como completo com ela)
    linhas += [{"ano": a, "mes": m, "metrica": "pago", "tema_codigo": "material_consumo", "subtema": "Outros",
                "valor_nominal": 1.0} for a, (n, _) in anos.items() for m in range(1, n + 1)]
    return pd.DataFrame(linhas)


@pytest.fixture
def ambiente(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "PROCESSED_DIR", tmp_path / "processed")
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    cat = pd.DataFrame([
        # automatico, reducao de 30% sobre 2024
        {"id": "E1-COPOS-01", "eixo_pls": "1", "unidade": "un", "tipo_meta": "reducao_vs_base", "meta_valor": "30",
         "ano_base": "2024", "automacao": "automatico", "tipo_fonte": "publica",
         "calculo": "ind:metrica=quantidade_itens,subtema=Copos descartáveis,campo=valor_nominal"},
        # lancado em total, dividido pela comunidade do INEP
        {"id": "E1-AGUA-01", "eixo_pls": "1", "unidade": "m³/pessoa", "tipo_meta": "reducao_vs_base", "meta_valor": "10",
         "ano_base": "2024", "automacao": "integracao", "tipo_fonte": "fornecedor", "calculo": "per_capita"},
        {"id": "E1-RU-01", "eixo_pls": "1", "unidade": "sim/não", "tipo_meta": "booleano", "meta_valor": "1",
         "ano_base": "", "automacao": "informado", "tipo_fonte": "documental", "calculo": ""},
    ])
    monkeypatch.setattr(catalogo, "carregar", lambda: catalogo.tipar(cat))
    save_processed(pd.DataFrame({"ano": [2023], "ufpb": [True], "comunidade": [1000]}), "pls_comunidade")
    save_processed(_meses({2024: (12, 1000.0), 2025: (12, 600.0), 2026: (3, 100.0)}), "pls_indicadores")
    (tmp_path / "metas").mkdir()
    return tmp_path / "metas" / "valores_informados.csv"


def test_metas_automatico_e_lancado(ambiente):
    from metas.load_metas import build

    ambiente.write_text(
        "indicador_id;ano;valor;fonte;informado_por;data_registro;observacao\n"
        "E1-AGUA-01;2024;20.000;CAGEPA;SINFRA;2026-09-23;\n"
        "E1-AGUA-01;2025;18.500;CAGEPA;SINFRA;2026-09-23;\n"
        "E1-RU-01;2025;1;Comissão;Comissão;2026-09-23;\n",
        encoding="utf-8",
    )
    df = build().set_index(["indicador_id", "ano"])

    assert df.loc[("E1-COPOS-01", 2024), "situacao"] == "linha_de_base"
    copos25 = df.loc[("E1-COPOS-01", 2025)]
    assert copos25["variacao_pct"] == pytest.approx(-40) and copos25["situacao"] == "atingida"
    # ano parcial que ja bateu a meta aparece como atingida; o que nao bateu fica em_andamento
    assert df.loc[("E1-COPOS-01", 2026), "ano_completo"] == False  # noqa: E712

    agua = df.loc[("E1-AGUA-01", 2025)]
    assert agua["valor"] == pytest.approx(18.5)  # m³ / 1000 pessoas (censo 2023, ultimo disponivel)
    assert agua["origem"] == "lancado+comunidade"
    assert agua["variacao_pct"] == pytest.approx(-7.5) and agua["situacao"] == "nao_atingida"

    assert df.loc[("E1-RU-01", 2025), "situacao"] == "atingida"


def test_ano_parcial_nao_reprova(ambiente):
    from metas.load_metas import build

    save_processed(_meses({2024: (12, 1000.0), 2025: (4, 900.0)}), "pls_indicadores")
    df = build().set_index(["indicador_id", "ano"])
    assert df.loc[("E1-COPOS-01", 2025), "situacao"] == "em_andamento"


def test_lancamento_fora_do_catalogo(ambiente):
    from metas.load_metas import build

    ambiente.write_text(
        "indicador_id;ano;valor;fonte;informado_por;data_registro;observacao\nX-99;2025;1;a;b;c;\n", encoding="utf-8"
    )
    with pytest.raises(ValueError, match="fora do catalogo"):
        build()


def test_percentual_por_razao(ambiente, monkeypatch):
    from metas.load_metas import _automatico

    ind = pd.DataFrame({
        "ano": [2025] * 3, "mes": [1] * 3, "metrica": ["consumo_litros"] * 3, "tema_codigo": ["deslocamento"] * 3,
        "subtema": ["Frota - diesel", "Frota - gasolina", "Frota - etanol"], "valor_nominal": [600.0, 300.0, 100.0],
    })
    calc = catalogo.parse_calculo(
        "ind:metrica=consumo_litros,subtema=Frota - etanol,campo=valor_nominal,"
        "razao_subtema=Frota - diesel|Frota - gasolina|Frota - etanol"
    )
    assert _automatico(calc, ind).to_dict() == {2025: pytest.approx(10.0)}


def test_ano_de_referencia_incompleto_nao_compara(ambiente):
    from metas.load_metas import build

    # 2024 so com dezembro: 2025 contra ele daria variacao enganosa
    save_processed(_meses({2024: (1, 100.0), 2025: (12, 900.0)}), "pls_indicadores")
    df = build().set_index(["indicador_id", "ano"])
    assert df.loc[("E1-COPOS-01", 2025), "situacao"] == "em_andamento"
    assert df.loc[("E1-COPOS-01", 2024), "ano_completo"] == False  # noqa: E712


def test_por_m2_e_razao_das_somas():
    # dois campi: (100 kWh / 10 m2) + (300 kWh / 90 m2) = 13,3 se somasse as razoes; o certo e 400/100
    from metas.load_metas import _automatico

    ind = pd.DataFrame([
        {"ano": 2025, "mes": m, "metrica": "consumo_kwh", "tema_codigo": "energia", "subtema": s,
         "valor_real": v / 12, "area_m2": a, "valor_por_m2": v / 12 / a}
        for m in range(1, 13) for s, v, a in (("Campus I", 100, 10.0), ("Campus II", 300, 90.0))
    ])
    calc = catalogo.parse_calculo("ind:metrica=consumo_kwh,campo=valor_por_m2")
    assert _automatico(calc, ind)[2025] == pytest.approx(4.0)
