from datetime import date

import pandas as pd

from acoes.load_acoes import COLUNAS_ACOMP
from formularios import formularios as f
from metas.load_metas import COLUNAS_LANCADOS
from saude import verificar as s


def test_envio_mais_recente_substitui_linha_do_csv():
    csv = pd.DataFrame([
        {**{c: "" for c in COLUNAS_ACOMP}, "acao_id": "T16-01", "ciclo": "2026-S2", "situacao": "nao_iniciada"},
        {**{c: "" for c in COLUNAS_ACOMP}, "acao_id": "T16-02", "ciclo": "2026-S2", "situacao": "em_andamento"},
    ])
    base = {c: "" for c in COLUNAS_ACOMP if c != "data_registro"}
    envios = pd.DataFrame([
        {**base, "acao_id": "T16-01", "ciclo": "2026-S2", "situacao": "em_andamento", "registrado_em": "2026-09-20T10:00:00"},
        {**base, "acao_id": "T16-01", "ciclo": "2026-S2", "situacao": "concluida", "evidencia": "SIPAC 1",
         "registrado_em": "2026-09-21T09:00:00"},
    ])
    novo, n = f.mesclar(csv, envios, ["acao_id", "ciclo"], COLUNAS_ACOMP)
    assert n == 1
    assert novo.set_index("acao_id")["situacao"].to_dict() == {"T16-01": "concluida", "T16-02": "em_andamento"}
    assert novo.set_index("acao_id").loc["T16-01", "data_registro"] == "2026-09-21"
    assert list(novo.columns) == COLUNAS_ACOMP


def test_valor_informado_em_formato_brasileiro():
    assert f._valor_br(1234.5) == "1234,5"
    assert f._valor_br(3.0) == "3"
    assert f._valor_br(None) == ""
    csv = pd.DataFrame(columns=COLUNAS_LANCADOS)
    envios = pd.DataFrame([{"indicador_id": "E6-CAMPANHA-01", "ano": "2025", "valor": "4", "fonte": "Ascom",
                            "informado_por": "Fulana", "observacao": "", "registrado_em": "2026-03-01T08:00:00"}])
    novo, n = f.mesclar(csv, envios, ["indicador_id", "ano"], COLUNAS_LANCADOS)
    assert n == 1 and novo.iloc[0]["data_registro"] == "2026-03-01"


def test_hash_do_token_nao_guarda_o_token():
    h = f.hash_token("abc")
    assert h != "abc" and len(h) == 64 and h == f.hash_token("abc")


def test_saude_evg_aponta_bimestre_sem_id(tmp_path, monkeypatch):
    from common import config
    (tmp_path / "evg_recursos.csv").write_text("ano;bimestre;titulo;drive_id\n2026;1;x;a\n", encoding="utf-8")
    monkeypatch.setattr(config, "REF_DIR", tmp_path)
    linhas = s.evg(date(2026, 6, 15))
    assert linhas[0]["nivel"] == "atencao"
    assert "2026 · bimestre 2 (2026/03–04)" in linhas[0]["detalhe"]
    assert not any("bimestre 3" in d and d.startswith("2026") for d in linhas[0]["detalhe"])  # mai-jun ainda nao saiu


def test_saude_falha_de_modulo_vira_erro_e_ordena_primeiro(monkeypatch):
    for nome in ("despesas", "faturas", "anomalias", "compras", "evg", "inep", "ipca", "cnpj", "acoes", "metas"):
        monkeypatch.setattr(s, nome, lambda hoje, n=nome: [s._linha(n, n, "ok", "tudo certo")])
    monkeypatch.setattr(s, "gee", lambda: [s._linha("gee_fator", "indicadores", "atencao", "fator provisório", ["2025"])])
    df = s.verificar(date(2026, 9, 25), falhas={"faturas": "ConnectionError: sipac fora"})
    assert df.iloc[0]["nivel"] == "erro" and df.iloc[0]["modulo"] == "faturas"
    assert df.iloc[1]["nivel"] == "atencao"
    texto = s.texto_alerta(df)
    assert "[ERRO] Módulo faturas falhou" in texto and "[ATENCAO] fator provisório" in texto
    assert "tudo certo" not in texto


def test_alerta_so_sai_com_smtp_configurado(monkeypatch):
    df = pd.DataFrame([{**s._linha("x", "x", "erro", "falhou"), "execucao": "2026-09-25T01:00:00"}])
    monkeypatch.delenv("SMTP_HOST", raising=False)
    monkeypatch.setenv("ALERTA_EMAILS", "a@ufpb.br")
    assert s.enviar_alerta(df) is False
