from datetime import date

import pandas as pd
import pytest

from common import config
from common.storage import save_processed

HOJE = date(2026, 9, 25)


def test_plano_real_e_valido():
    from acoes.load_acoes import plano

    p = plano()
    assert len(p) == 70 and p["id"].is_unique
    assert set(p.loc[p["id"].str.startswith("T"), "tabela_pls"]) == {str(t) for t in range(16, 25)}
    cat = pd.read_csv(config.REF_DIR / "indicadores_pls.csv", sep=";", dtype=str)
    assert set(p["indicador_id"]) - {""} <= set(cat["id"])


@pytest.fixture
def ambiente(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "PROCESSED_DIR", tmp_path / "processed")
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    save_processed(pd.DataFrame([
        {"periodo": "2026-07", "metrica": "consumo_m3", "subtema": "Campus I", "valor_nominal": 100.0},
        {"periodo": "2025-01", "metrica": "consumo_litros", "subtema": "Frota - diesel", "valor_nominal": 50.0},
    ]), "pls_indicadores")
    return tmp_path / "metas" / "acompanhamento_acoes.csv"


def _escreve(arq, linhas):
    arq.parent.mkdir(parents=True, exist_ok=True)
    cab = "acao_id;ciclo;situacao;percentual;evidencia;justificativa;facilitadores;dificuldades;ajuste_sugerido;informado_por;data_registro\n"
    arq.write_text(cab + "".join(";".join(l) + "\n" for l in linhas), encoding="utf-8")


def test_cria_modelo_do_ciclo_quando_nao_existe(ambiente):
    from acoes.load_acoes import build

    df, resumo = build(HOJE)
    modelo = pd.read_csv(ambiente, sep=";", dtype=str, keep_default_na=False)
    assert len(modelo) == 70 and set(modelo["ciclo"]) == {"2026-S2"}
    assert resumo["acoes"] == 70


def test_situacao_contra_o_prazo(ambiente):
    from acoes.load_acoes import build

    _escreve(ambiente, [
        # T19-01 (entrega, fim jan/2026) concluida com evidencia
        ["T19-01", "2026-S1", "concluida", "100", "SIPAC 23074.1/2026-00", "", "", "", "", "SINFRA", "2026-07-01"],
        # T16-02 (entrega, fim set/2026) em andamento: ainda no prazo
        ["T16-02", "2026-S1", "em_andamento", "40", "", "", "", "", "", "SINFRA", "2026-07-01"],
        # T20-03 (entrega, fim jun/2025) sem conclusao: atrasada
        ["T20-03", "2026-S1", "em_andamento", "80", "", "Aguardando projeto", "", "", "", "SINFRA", "2026-07-01"],
        # T18-01 (continua) concluida sem evidencia: nao conta
        ["T18-01", "2026-S1", "realizada_no_ciclo", "", "", "", "", "", "", "CGA", "2026-07-01"],
    ])
    df, resumo = build(HOJE)
    sit = df.set_index("id")["situacao"]
    assert sit["T19-01"] == "concluida" and sit["T16-02"] == "em_andamento" and sit["T20-03"] == "atrasada"
    assert sit["T18-01"] == "em_dia" and df.set_index("id").loc["T18-01", "sem_evidencia"]
    # continua verificada pelo painel: agua com dado recente (jul/2026) fica em dia sem ninguem informar
    assert sit["T16-03"] == "em_dia"
    # combustivel com ultimo dado em jan/2025: nao comprova o ciclo
    assert sit["T19-09"] == "sem_informacao"
    assert sit["T17-03"] == "sem_informacao"  # entrega que comeca no mes atual, sem informacao ainda
    assert resumo["atrasadas"] >= 1 and 0 < resumo["indice_cumprimento"] < 100


def test_rejeita_acao_ou_situacao_desconhecida(ambiente):
    from acoes.load_acoes import build

    _escreve(ambiente, [["X-99", "2026-S1", "concluida", "", "", "", "", "", "", "", ""]])
    with pytest.raises(ValueError, match="fora do plano"):
        build(HOJE)
    _escreve(ambiente, [["T19-01", "2026-S1", "feito", "", "", "", "", "", "", "", ""]])
    with pytest.raises(ValueError, match="situacao invalida"):
        build(HOJE)
