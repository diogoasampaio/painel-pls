import io

import openpyxl
import pandas as pd
import pytest

from fator_sin import load_fator_sin as fs
from indicadores import build_indicadores as bi

MESES = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro",
         "Novembro", "Dezembro"]


def _planilha(blocos: dict[int, tuple[list, float | None]]) -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    for ano, (valores, anual) in blocos.items():
        ws.append(["Fator Médio Mensal (tCO2/MWh)"] + [None] * 13 + ["Fator Médio Anual (tCO2/MWh)"])
        ws.append([ano, None, "MÊS"] + [None] * 11 + [f"ANO - {ano}"])
        ws.append([None, None, *MESES, anual])
        ws.append([None, None, *valores])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_le_mensal_e_anual_e_para_no_ultimo_mes_publicado():
    xlsx = _planilha({2025: ([0.02] * 12, 0.0461), 2026: ([0.0458, 0.049] + [None] * 10, None)})
    df = fs.ler(xlsx, "Inventario_2026_janfev.xlsx")
    assert len(df) == 14 and df["periodo"].iloc[-1] == "2026-02"
    assert df.loc[df["periodo"] == "2025-05", "fator_anual_t_mwh"].iloc[0] == 0.0461
    assert df.loc[df["periodo"] == "2026-01", "fator_anual_t_mwh"].isna().all()


def test_recusa_unidade_errada():
    with pytest.raises(RuntimeError):
        fs.ler(_planilha({2025: ([38.5] * 12, 46.1)}))  # kg/MWh em vez de t/MWh


def test_link_da_planilha_na_pagina():
    html = '<a href="https://www.gov.br/mcti/x/arquivo/Despacho_2026.xlsx">d</a>' \
           '<a href="/mcti/pt-br/y/arquivo/Inventario_2026_janago.xlsx">Aqui</a>'
    assert fs.link_planilha(html) == "https://www.gov.br/mcti/pt-br/y/arquivo/Inventario_2026_janago.xlsx"


def test_mes_sem_fator_usa_anual_do_ultimo_ano_fechado(monkeypatch):
    f = pd.DataFrame({"periodo": ["2025-12", "2026-01"], "ano": [2025, 2026], "mes": [12, 1],
                      "fator_t_mwh": [0.0486, 0.0458], "fator_anual_t_mwh": [0.0461, None]})
    monkeypatch.setattr(bi, "load_processed", lambda nome: f)
    sin = bi._fatores_sin()
    assert sin["2026-01"] == (0.0458, False)
    assert sin["2026-09"] == (0.0461, True)
