import pandas as pd
import pytest

from common import config
from common.storage import save_processed

# cabecalhos reais: jan-fev/2023 (';', datas dd/mm/aaaa, nome e CPF parcial) e 2026 ('|', codigo_pessoa)
CSV_2023 = [
    "cod_matricula;dt_matricula;cpf;nome;sexo;data_nascimento;nacionalidade;login_liferay;cod_turma;nome_turma;"
    "modalidade_turma;cod_curso;nome_curso;carga_horaria;dt_inicio_insc;dt_fim_insc;dt_inicio;dt_fim;sit_turma;"
    "sit_matricula;poder;esfera;instituicao;municipio_pessoa;uf_pessoa;conteudista;tematica;uf_servidor;municipio_servidor",
    "1;05/01/2023 10:00;***.111.222-**;FULANA DE TAL;feminino;1980;BR;-;9;T;A distância;500;Introdução à Agenda 2030;20;"
    ";;;;CONCLUIDA;Concluida;Executivo;Federal;Universidade Federal da Paraíba;João Pessoa;PB;Enap;Meio Ambiente;PB;",
    "2;06/01/2023 11:00;***.111.222-**;FULANA DE TAL;feminino;1980;BR;-;9;T;A distância;501;Gestão de Riscos;30;"
    ";;;;CONCLUIDA;Concluida;Executivo;Federal;Universidade Federal da Paraíba;João Pessoa;PB;Enap;Gestão;PB;",
    "3;07/01/2023 12:00;***.999.888-**;OUTRA PESSOA;feminino;1990;BR;-;9;T;A distância;500;Introdução à Agenda 2030;20;"
    ";;;;CONCLUIDA;Concluida;Executivo;Federal;Instituto Federal da Paraíba;João Pessoa;PB;Enap;Meio Ambiente;PB;",
]
CSV_2026 = [
    "cod_matricula|dt_matricula|cod_curso|nome_curso|cod_turma|nome_turma|modalidade_turma|carga_horaria|dt_inicio_insc|"
    "dt_fim_insc|dt_inicio|dt_fim|conteudista|tematica|sit_matricula|codigo_pessoa|sexo|idade|deficiencia|raca|"
    "nacionalidade|uf_pessoa|municipio_pessoa|instituicao|poder|esfera|uf_servidor|municipio_servidor",
    "a1|2026-03-10 09:00:00|700|Diversidade e inclusão no ambiente de trabalho|t|T|A distância|10|||||Enap|Pessoas|"
    "Concluída|p1|f|30||||PB|João Pessoa|UNIVERSIDADE FEDERAL DA PARAIBA|Executivo|Federal||",
    "a2|2026-04-10 09:00:00|701|Contratações Sustentáveis|t|T|A distância|40|||||Enap|Compras|"
    "Não Concluído|p1|f|30||||PB|João Pessoa|Universidade Federal da Paraíba|Executivo|Federal||",
]


def test_filtra_ufpb_e_descarta_dado_pessoal():
    from evg.load_evg import filtrar_ufpb

    regs = filtrar_ufpb(CSV_2023)
    assert [r["cod_matricula"] for r in regs] == ["1", "2"]  # IFPB fica de fora
    assert all("nome" not in r and "cpf" not in r for r in regs)
    assert regs[0]["pessoa"] == regs[1]["pessoa"] and "FULANA" not in regs[0]["pessoa"]
    regs26 = filtrar_ufpb(CSV_2026)  # outra ordem de colunas, instituicao sem acento
    assert [r["pessoa"] for r in regs26] == ["p1", "p1"]


def test_transforma_e_classifica_sustentabilidade():
    from evg.load_evg import filtrar_ufpb, transform

    regs = [{**r, "ano_arquivo": 2023, "bimestre": 1} for r in filtrar_ufpb(CSV_2023)]
    regs += [{**r, "ano_arquivo": 2026, "bimestre": 2} for r in filtrar_ufpb(CSV_2026)]
    df = transform(regs).set_index("cod_matricula")
    assert df.loc["1", "periodo"] == "2023-01" and df.loc["a1", "periodo"] == "2026-03"
    assert df["concluida"].to_dict() == {"1": True, "2": True, "a1": True, "a2": False}
    # "ambiente de trabalho" nao e sustentabilidade; Agenda 2030 e contratacoes sustentaveis sao
    assert df["sustentabilidade"].to_dict() == {"1": True, "2": False, "a1": False, "a2": True}


def test_pessoas_em_sustentabilidade_contadas_uma_vez_por_ano(tmp_path, monkeypatch):
    from indicadores import build_indicadores as b

    monkeypatch.setattr(config, "PROCESSED_DIR", tmp_path)
    evg = pd.DataFrame([
        {"periodo": "2025-02", "ano": 2025, "pessoa": "p1", "concluida": True, "sustentabilidade": True, "carga_horaria": 20},
        {"periodo": "2025-05", "ano": 2025, "pessoa": "p1", "concluida": True, "sustentabilidade": True, "carga_horaria": 10},
        {"periodo": "2025-05", "ano": 2025, "pessoa": "p2", "concluida": True, "sustentabilidade": True, "carga_horaria": 5},
        {"periodo": "2025-06", "ano": 2025, "pessoa": "p3", "concluida": False, "sustentabilidade": True, "carga_horaria": 5},
    ])
    save_processed(evg, "pls_evg")
    ind = b._evg().set_index(["metrica", "periodo"])["valor"]
    assert ind[("evg_pessoas_sust", slice(None))].sum() == 2  # p1 uma vez (fev), p2 (mai); p3 nao concluiu
    assert ind[("evg_certificados", slice(None))].sum() == 3
    assert ind[("evg_horas_certificadas", slice(None))].sum() == pytest.approx(35)


def test_arquivo_sem_cabecalho():
    # nov-dez/2024 veio sem a linha de titulos
    from evg.load_evg import CABECALHO_27, filtrar_ufpb

    linha = dict.fromkeys(CABECALHO_27, "")
    linha.update(cod_matricula="x1", dt_matricula="2024-11-12 22:46:05", instituicao="Universidade Federal da Paraíba",
                 codigo_pessoa="h1", sit_matricula="Concluida", nome_curso="Curso")
    outra = {**linha, "cod_matricula": "x2", "instituicao": "Outra"}
    regs = filtrar_ufpb(["|".join(linha[c] for c in CABECALHO_27), "|".join(outra[c] for c in CABECALHO_27)])
    assert [r["cod_matricula"] for r in regs] == ["x1"]


def test_cabecalho_com_bom():
    from evg.load_evg import filtrar_ufpb

    regs = filtrar_ufpb(["﻿" + CSV_2023[0], *CSV_2023[1:]])
    assert [r["cod_matricula"] for r in regs] == ["1", "2"]
