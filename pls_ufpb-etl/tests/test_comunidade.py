import pandas as pd
import pytest

from common import comunidade, config
from common.storage import save_processed


@pytest.fixture
def inep(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "PROCESSED_DIR", tmp_path)
    save_processed(pd.DataFrame({
        "ano": [2022, 2023], "co_ies": ["579", "579"], "ufpb": [True, True],
        "docentes_exercicio": [100, 110], "tecnicos": [50, 55], "matriculas": [800, 900], "comunidade": [950, 1065],
    }), "pls_comunidade")


def test_planilha_da_ufpb_tem_prioridade_e_inep_cobre_o_resto(inep):
    comunidade.ARQUIVO.write_text(
        "ano;discentes;docentes;tecnicos;terceirizados;comunidade\n2023;1000;120;60;20;1200\n2024;1100;125;60;15;1300\n",
        encoding="utf-8",
    )
    tab = comunidade.ufpb()
    assert tab.loc[2022, "fonte"] == comunidade.FONTE_INEP and tab.loc[2022, "comunidade"] == 950
    assert tab.loc[2023, "fonte"] == comunidade.FONTE_UFPB and tab.loc[2023, "comunidade"] == 1200
    assert tab.loc[2023, "servidores"] == 180  # docentes + tecnicos, sem terceirizados

    valor, ano = comunidade.por_ano(pd.Series([2022, 2024, 2026]), "comunidade")
    assert valor.tolist() == [950, 1300, 1300]  # 2026 sem contagem: usa a de 2024
    assert ano.tolist() == [2022, 2024, 2024]


def test_importar_confere_a_soma(tmp_path):
    xlsx = tmp_path / "comunidade.xlsx"
    pd.DataFrame({
        "ANO": [2025], "COMUNIDADE_ACADEMICA": [999], "DISCENTES_UFPB": [800], "Docentes": [100],
        "TECNICOS_ADMINISTRATIVOS_UFPB": [50], "TERCEIRIZADOS_UFPB": [40],
    }).to_excel(xlsx, index=False)
    with pytest.raises(ValueError, match="2025"):
        comunidade.importar(str(xlsx))
