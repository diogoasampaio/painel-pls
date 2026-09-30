"""Especificacao do pedido de dados de estudantes a STI (todos os niveis) -> Word.

    python relatorios/gerar_pedido_sti.py [--saida DIR]

Layout dos arquivos: ref/modelos_sti/dicionario_estudantes.csv (o mesmo que o
modulo do painel vai ler). Modelos com uma linha de exemplo em
ref/modelos_sti/modelo_*.csv.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

import pandas as pd

ETL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ETL))
from relatorios.blocos import Doc, docx_doc  # noqa: E402

DIC = ETL / "ref" / "modelos_sti" / "dicionario_estudantes.csv"


def montar() -> tuple[Doc, dict]:
    dic = pd.read_csv(DIC, sep=";", dtype=str, keep_default_na=False)
    doc = Doc()

    doc.h1("Objetivo")
    doc.p("O Painel de Sustentabilidade da UFPB calcula indicadores do Plano de Logística Sustentável (PLS) por pessoa, "
          "como o consumo de água por membro da comunidade acadêmica (meta do PLS: reduzir 10% sobre 2024). Hoje o "
          "número de estudantes vem do Censo da Educação Superior do INEP, que tem dois problemas:")
    doc.lista(["**Defasagem:** o censo de um ano sai no fim do ano seguinte; em 2026 o painel ainda usa 2024.",
               "**Cobertura:** só a graduação. Ficam de fora especialização, residências, mestrado, doutorado, cursos "
               "técnicos e educação básica, e não há recorte por campus nem por período."])
    doc.p("Pedimos à STI uma extração agregada do SIGAA, por período letivo, curso e campus, para todos os níveis de "
          "ensino. Nenhum dado pessoal sai da STI: só contagens.")

    doc.h1("Quem conta como estudante")
    doc.p("**Critério principal:** pessoa com vínculo ativo que esteja matriculada em pelo menos um componente curricular "
          "ou atividade acadêmica no período letivo. Atividade acadêmica inclui TCC, estágio, internato, prática, "
          "elaboração de dissertação ou tese e residência, que na pós-graduação e na saúde substituem as disciplinas.")
    doc.p("A unidade de contagem é o **período letivo**, não o ano. Quem se matricula num período conta naquele período. "
          "O painel calcula depois a população do ano como a média dos períodos regulares, que representa quem está "
          "nos campi ao longo do ano. A contagem de pessoas distintas no ano (arquivo 2) serve para o total da "
          "comunidade e para a conferência com o INEP.")
    doc.tabela("Situações e como contam", ["Situação no período", "Conta como estudante?", "Campo"], [
        ["Vínculo ativo e matriculado em componente ou atividade", "**Sim**", "`qt_matriculados`"],
        ["Vínculo ativo sem nenhuma matrícula (não trancado)", "Não, informado à parte", "`qt_ativos_sem_matricula`"],
        ["Matrícula trancada (estoque no fim do período)", "Não", "`qt_trancados`"],
        ["Em mobilidade ou intercâmbio fora da UFPB", "Não (não está nos campi)", "`qt_mobilidade_saida`"],
        ["Aluno especial (sem vínculo com curso), matriculado em componente", "Não no total, informado à parte",
         "`qt_alunos_especiais`"],
        ["Concluiu no período", "Sim, se estava matriculado no período", "`qt_matriculados` e `qt_concluintes`"],
        ["Cancelado, jubilado, abandono ou transferido no período", "Sim, se chegou a se matricular no período",
         "`qt_matriculados` e `qt_desvinculados`"],
        ["Educação a distância", "Sim, separado pela modalidade", "`modalidade = distancia`"],
    ], larg=[3.2, 2.2, 2.2])
    doc.h2("Regras complementares")
    doc.lista([
        "**Períodos especiais** (férias, extraordinários) vêm marcados como `especial` e não entram na média do ano.",
        "**Cursos de regime anual** (técnico integrado, educação básica) usam `periodo = 0`, com o ano letivo inteiro.",
        "**Mesma pessoa em dois cursos ou níveis:** no arquivo 1 conta nos dois (é o vínculo de cada curso); no "
        "arquivo 2 conta uma vez, no vínculo principal (o de maior nível e, em empate, o mais recente).",
        "**Campus:** o de oferta do curso. No EAD, `campus = EAD` e o município do polo em `municipio_oferta`.",
        "**Residência médica e multiprofissional:** entram como nível próprio, mesmo quando geridas fora do SIGAA "
        "(se for o caso, informar a origem).",
        "**Estudante que também é servidor:** conta como estudante nos arquivos, e o arquivo 2 informa quantos são "
        "servidores, para o painel não contar a mesma pessoa duas vezes na comunidade acadêmica.",
    ])

    for arq, titulo, texto in [
        ("estudantes_periodo", "Arquivo 1: estudantes por período, curso e campus",
         "Uma linha por período letivo e curso (ou programa). Nome do arquivo: `estudantes_periodo_AAAA.csv`, um por ano."),
        ("estudantes_pessoas_ano", "Arquivo 2: pessoas distintas por ano e campus",
         "Uma linha por ano, campus, nível principal e modalidade, com pessoas sem dupla contagem. Nome do arquivo: "
         "`estudantes_pessoas_ano.csv`."),
    ]:
        doc.h1(titulo)
        doc.p(texto)
        x = dic[dic["arquivo"] == arq]
        doc.tabela(f"Layout do arquivo {arq}", ["Campo", "Tipo", "Obrig.", "Descrição", "Exemplo"],
                   [[f"`{r.campo}`", r.tipo, r.obrigatorio, r.descricao, r.exemplo] for r in x.itertuples()],
                   larg=[1.9, 0.8, 0.6, 3.6, 1.3])
        doc.nota("Os exemplos são ilustrativos. O modelo com uma linha de exemplo está em "
                 f"`ref/modelos_sti/modelo_{arq}.csv`.")

    doc.h1("Formato, período e entrega")
    doc.lista([
        "**Formato:** CSV em UTF-8, separador ponto e vírgula, cabeçalho com os nomes de campo acima, datas "
        "AAAA-MM-DD, números inteiros sem separador de milhar.",
        "**Primeira entrega:** 2022 a 2025 completos e o 1º período de 2026, para refazer a série desde a linha de "
        "base do PLS (2024).",
        "**Depois:** a cada período letivo, até 30 dias após o fim do período (arquivo 1), e o arquivo 2 do ano "
        "até 28 de fevereiro do ano seguinte.",
        "**Canal preferido:** publicação como conjunto de dados no portal de dados abertos da UFPB "
        "(dadosabertos.ufpb.br), que já publica cursos e discentes da graduação. O painel lê o arquivo sozinho a "
        "cada carga. Alternativas: pasta compartilhada fixa ou uma visão (view) de leitura no banco do SIGAA.",
    ])

    doc.h1("Conferências que o painel fará")
    doc.lista([
        "Graduação: pessoas matriculadas no ano (arquivo 2) comparadas com as matrículas do Censo do INEP do mesmo "
        "ano, por curso, pelo código INEP. As duas contam quem esteve cursando ou se formou no ano.",
        "Mestrado e doutorado: comparação com os discentes da Plataforma Sucupira (CAPES) por programa.",
        "Consistência interna: soma dos campi igual ao total; matriculados do período não maiores que os vínculos "
        "do curso; um período por curso sem duplicidade.",
        "Divergências acima de 5% são apontadas na verificação automática da carga e enviadas à STI.",
    ])

    doc.h1("Proteção de dados (LGPD)")
    doc.p("Os arquivos só têm contagens por curso, período e campus. Não pedimos nome, CPF, matrícula, data de "
          "nascimento, sexo, cor ou raça, nem qualquer dado que identifique pessoas. A deduplicação de pessoas entre "
          "cursos e níveis e o cruzamento com servidores são feitos dentro da STI, e só os totais saem.")

    doc.h1("Contato")
    doc.pendente("Nome, setor e e-mail do responsável pelo painel na PROPLAN/Comissão Gestora do PLS e do responsável "
                 "na STI.")
    hoje = date.today().strftime("%d/%m/%Y")
    meta = {"titulo": "Pedido de Dados de Estudantes", "eyebrow": "UFPB · Painel de Sustentabilidade",
            "h1": "Pedido de dados de estudantes à STI", "subtitulo": "Especificação da extração do SIGAA",
            "lead": "Critério de aluno, layout dos arquivos, regras de contagem e entrega.",
            "selo": f"Versão de {hoje}",
            "nota_capa": f"Especificação preparada pelo Painel de Sustentabilidade da UFPB em {hoje}, para os "
                         f"indicadores por pessoa do PLS.",
            "rodape_doc": "Pedido de dados de estudantes à STI", "rodape_html": "", "toc_niveis": 1}
    return doc, meta


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--saida", type=Path, default=Path(__file__).parent)
    a = ap.parse_args(argv)
    doc, meta = montar()
    a.saida.mkdir(parents=True, exist_ok=True)
    arq = a.saida / "pedido_dados_estudantes_sti.docx"
    docx_doc(doc, meta, arq)
    print(arq)


if __name__ == "__main__":
    main()
