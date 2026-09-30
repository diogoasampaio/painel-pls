"""Relatorio de construcao do dado de cada indicador do PLS UFPB: fontes,
passo a passo, regras e filtros, calculo ano a ano, conferencias e limites.
Numeros lidos dos parquet do ETL (os mesmos do painel)."""

import html
import math
import sys
from datetime import date
from pathlib import Path

import pandas as pd

ETL = Path(r"C:\Users\diogo\repositorios\codeinfo\sustentabilidade\pls_ufpb-etl")
OUT = Path(__file__).with_name("construcao_indicadores.html")
PROC = ETL / "data" / "processed"
sys.path.insert(0, str(ETL))
from common import comunidade as com_ufpb  # noqa: E402
from metas import catalogo  # noqa: E402

COMUNIDADE = com_ufpb.ufpb()

e = html.escape
ANOS = [2023, 2024, 2025, 2026]

cat = pd.read_csv(ETL / "ref" / "indicadores_pls.csv", sep=";", dtype=str, keep_default_na=False)
eixos = pd.read_csv(ETL / "ref" / "eixos_pls.csv", sep=";", dtype=str).set_index("eixo_pls")["eixo"]
mapa = pd.read_csv(ETL / "ref" / "mapeamento_natureza_pls.csv", sep=";", dtype=str, keep_default_na=False)
regras = pd.read_csv(ETL / "ref" / "regras_texto_pls.csv", sep=";", dtype=str, keep_default_na=False).set_index("subtema")
acoes = pd.read_csv(ETL / "ref" / "acoes_pls.csv", sep=";", dtype=str, keep_default_na=False)
fatores = pd.read_csv(ETL / "ref" / "fatores_emissao.csv", sep=";")
area = pd.read_csv(ETL / "ref" / "area_construida.csv", sep=";", dtype={"area_m2": float})
corrigidos = pd.read_csv(ETL / "ref" / "processos_corrigidos.csv", sep=";", dtype=str)
ind = pd.read_parquet(PROC / "pls_indicadores.parquet")
metas = pd.read_parquet(PROC / "pls_metas.parquet")
faturas = pd.read_parquet(PROC / "pls_faturas.parquet")
REF_IPCA = str(ind["ref_ipca"].dropna().max())
REF_IPCA_TXT = f"{REF_IPCA[5:]}/{REF_IPCA[:4]}"

PORTAL_DESPESAS = "https://portaldatransparencia.gov.br/download-de-dados/despesas"
PORTAL_VIAGENS = "https://portaldatransparencia.gov.br/download-de-dados/viagens"
SIPAC = "https://sipac.ufpb.br/public/jsp/portal.jsf"
BCB = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.433/dados"
INEP = "https://www.gov.br/inep/pt-br/acesso-a-informacao/dados-abertos/microdados/censo-da-educacao-superior"
TG = "Tesouro Gerencial (extração da PROPLAN para 2024)"


def num(v, unidade: str = "", casas: int | None = None) -> str:
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "—"
    if casas is None:
        casas = 0 if abs(v) >= 100 or v == 0 else (1 if abs(v) >= 10 else 2)
    s = f"{v:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    if unidade.startswith("R$"):
        return "R$ " + s + unidade[2:]
    return f"{s} {unidade}".strip()


def fonte(nome: str, url: str | None, oque: str) -> str:
    link = f'<a href="{e(url)}" target="_blank" rel="noopener">{e(nome)}</a>' if url else e(nome)
    return f"<li><b>{link}</b>: {e(oque)}</li>"


# ---------------------------------------------------------------- familias de construcao

def _meses_carregados(metrica: str) -> dict:
    if metrica in ("contratacoes_pncp", "contratacoes_pncp_valor", "editais_marcadores", "compras_compartilhadas"):
        metrica = "contratacoes_pncp"
    base = "pago" if metrica in ("empenhado_itens", "pago_acao", "empenhado_material_consumo", "pago_fornecedores") else ("evg_matriculas" if metrica.startswith("evg_") else metrica)
    return ind[ind["metrica"] == base].groupby("ano")["mes"].nunique().to_dict()


FONTES_DESPESA = [
    ("Arquivos diários de despesas do Portal da Transparência (CGU, dados abertos)", PORTAL_DESPESAS,
     "empenhos, liquidações e pagamentos de cada dia, com natureza de despesa de 8 dígitos, favorecido e observação; filtrados para o órgão 26240 e as UGs 153065, 153066, 153073 e 153074"),
    ("IPCA mensal (IBGE, série 433 do Banco Central)", BCB, f"correção dos valores para R$ de {REF_IPCA_TXT}"),
]
PASSOS_DESPESA = [
    "Baixar o arquivo diário de despesas do Portal para cada dia da janela (2023 em diante), com pausas para não ser bloqueado pelo servidor da CGU, e guardar só as linhas das 4 UGs da UFPB (<code>despesas/portal_bulk.py</code>).",
    "Para cada pagamento, ler os empenhos impactados: natureza de despesa completa (8 dígitos), valor pago e restos a pagar pagos. O valor do pagamento = pago no ano + restos a pagar pagos (<code>despesas/load_despesas.py</code>).",
    "Classificar a natureza de despesa num tema e subtema do PLS pela tabela <code>ref/mapeamento_natureza_pls.csv</code> (prefixo mais longo vence).",
    "Somar por mês (data do pagamento), tema e subtema; corrigir cada mês pelo IPCA (índice de " + REF_IPCA_TXT + " ÷ índice do mês) e guardar também o nominal (<code>indicadores/build_indicadores.py</code>).",
    "Somar os 12 meses do ano (<code>metas/load_metas.py</code>). Ano com menos de 12 meses carregados fica marcado como parcial.",
]
CONFERE_DESPESA = [
    f"{TG}: liquidado confere ao centavo em 211 de 211 pares mês × natureza de 2024; pago em 277 de 278 (única diferença: dez/2024, natureza 33903701, +R$ 34 mil).",
    "Tabelas 10, 12 e 13 do PLS (fonte PROPLAN): o pago de 2023 bate ao centavo com água, energia e combustível para outras finalidades.",
]
LIMITE_DESPESA = [
    "Regime de caixa: o gasto é contado no mês do pagamento, não no da competência (a fatura de dezembro paga em janeiro entra no ano seguinte).",
    "Dias sem arquivo publicado pela CGU ficam de fora até a publicação (sem chave da API do Portal não há como cobri-los).",
]

FONTES_FATURA = [
    ("Arquivos diários de despesas do Portal da Transparência", PORTAL_DESPESAS,
     "cada pagamento traz o número do processo de pagamento no SIPAC"),
    ("Consulta pública de processos do SIPAC/UFPB", SIPAC,
     "processo de pagamento com os documentos anexados em PDF (sem login nem CAPTCHA)"),
]
PASSOS_FATURA_COMUM = [
    "Selecionar no cache do Portal os pagamentos da natureza de despesa do tipo e extrair o número do processo (campo processo; se vazio, o número citado na observação). Normalizar os formatos gravados pelo Portal (<code>23074.</code>, só dígitos, ponto no fim, zero à esquerda faltando) e aplicar as correções de digitação conferidas em <code>ref/processos_corrigidos.csv</code>.",
    "Conferir o dígito verificador do número (NUP: DV = 98 − (radical+número+ano × 100) mod 97). DV inválido é número digitado errado no Portal: procurar na base aberta de processos da UFPB (dadosabertos.ufpb.br) o processo do mesmo ano, com o DV digitado, o assunto do tipo (unidade, interessado e assunto detalhado) e até 2 dígitos de diferença. Com candidato único, ele substitui o número; sem candidato único, os candidatos vão para a verificação de saúde (<code>faturas/processos_ufpb.py</code>).",
    "Consultar o processo na consulta pública do SIPAC (uma requisição a cada 2 s). Se o dígito verificador não bate, repetir com DV <code>99</code>, que o SIPAC aceita para buscar só por número e ano (<code>faturas/sipac.py</code>).",
    "Listar os documentos do processo e escolher o anexo pela espécie (FATURA, RELATÓRIO, PLANILHA, ANEXO…) e pelo nome do arquivo, sem baixar os demais.",
]
PASSOS_FATURA_FIM = [
    "Guardar o resultado do processo em <code>data/raw/sipac/&lt;ano&gt;/&lt;processo&gt;.json</code> (não é consultado de novo) e apagar o PDF (<code>faturas/load_faturas.py</code>).",
]

FAMILIAS = {
    "consumo_kwh": {
        "fontes": FONTES_FATURA,
        "passos": [
            *PASSOS_FATURA_COMUM,
            "Ler o PDF da Energisa (<code>faturas/leitores.py</code>): a página 1 (“Resumo das faturas”) dá uma linha por unidade consumidora com kWh faturado (ponta + fora ponta), demanda e valor; as DANF3E das páginas seguintes dão o kWh <b>medido</b> no quadro de medição.",
            "Usar o kWh medido quando existe e é compatível com o faturado (medido ≤ faturado × 1,05); senão, o faturado. Fatura com tarifa implícita fora de R$ 0,25 a R$ 4,00/kWh é marcada como suspeita e relida.",
            "Atribuir o mês de referência da fatura (não o do pagamento) e o campus do processo (observação do Portal ou assunto do processo no SIPAC).",
            *PASSOS_FATURA_FIM,
            "Somar os kWh por mês de referência e campus (<code>indicadores/build_indicadores.py</code>, métrica <code>consumo_kwh</code>) e depois pelos meses do ano.",
        ],
        "regras": ["Natureza de despesa 33903943 (Serviços de energia elétrica), favorecido Energisa Paraíba.",
                   "Campus: CAMPUS I/II/III/IV na observação do pagamento; desde 2026, no assunto do processo."],
        "confere": ["45 de 49 unidades consumidoras de 2024 com kWh do resumo igual ao medido na DANF3E (as outras 4 são cobradas pelo mínimo ou pela média).",
                    "Consumo total de 15,9 milhões de kWh em 2024, coerente com os R$ 10,8 milhões de energia pagos no Portal (≈ R$ 0,68/kWh com impostos).",
                    "Todos os meses de jan/2024 a jul/2026 presentes nos 4 campi."],
        "limites": ["A partir de 2026 o resumo usa o número novo da UC e a DANF3E a matrícula antiga: vale o kWh do resumo (faturado).",
                    "Não inclui energia gerada nas usinas fotovoltaicas próprias (consumo da rede)."],
    },
    "consumo_m3": {
        "fontes": FONTES_FATURA,
        "passos": [
            *PASSOS_FATURA_COMUM,
            "Ler a “fatura agrupada” da CAGEPA (<code>faturas/leitores.py</code>): uma linha por ligação com leitura anterior, leitura atual, m³ medido e m³ faturado.",
            "Usar o m³ medido; se ele passa de 5 × faturado + 100 (troca de hidrômetro, como os 72.055 m³ de jun/2024), usar o faturado.",
            "Atribuir o mês de referência da fatura e o campus (observação do Portal ou assunto do processo no SIPAC).",
            *PASSOS_FATURA_FIM,
            "Somar os m³ por mês de referência e campus (métrica <code>consumo_m3</code>) e depois pelos meses do ano.",
        ],
        "regras": ["Natureza de despesa 33903944 (Serviços de água e esgoto), favorecido CAGEPA.",
                   "Campus: CAMPUS I/II/III/IV na observação do pagamento; desde 2026, no assunto do processo (“Pagamento fatura da CAGEPA Campus IV – mês 03/2026”)."],
        "confere": ["Dezembro/2024 bate exatamente com a Tabela 11 do PLS: 12.833, 4.589 e 1.107 m³ nos Campi I, II e IV.",
                    "O valor bruto da fatura agrupada confere com o pago no Portal.",
                    "Todos os meses de jan/2024 a jul/2026 presentes nos 4 campi."],
        "limites": ["O Campus I caiu de ≈ 12 mil para ≈ 1 mil m³/mês na ligação principal (726486) em 2025: o dado está correto, a causa precisa ser explicada pela SINFRA.",
                    "Campus III (Bananeiras) quase não aparece nas faturas da CAGEPA (0 m³ em 2024, 79 m³ em 2025): confirmar com a SINFRA de onde vem a água do campus."],
    },
    "consumo_litros": {
        "fontes": FONTES_FATURA,
        "passos": [
            *PASSOS_FATURA_COMUM,
            "Ler o relatório de abastecimentos da gerenciadora de frota (<code>faturas/combustivel.py</code>), um registro por abastecimento: data, placa, combustível, litros, preço, valor bruto e líquido, posto, cidade, subunidade. Quatro modelos: extrato GOLDI (até mai/2024), “Abastecimentos” PRIME (set/2024–set/2025), “Relatório de Abastecimento/Faturamento” (out–nov/2025) e “Conferência NFe ANP” (dez/2025 em diante).",
            "Descartar condutor, matrícula e cartão (LGPD) e linhas de taxa zeradas; remover duplicatas (o mesmo relatório anexado ao processo principal e ao de retenção).",
            "Classificar o combustível (diesel, gasolina, etanol) pelo texto do produto e o campus pela subunidade: CCA = II, CCHSA = III, CCAE = IV, demais = I.",
            *PASSOS_FATURA_FIM,
            "Somar os litros por mês do abastecimento e combustível (métrica <code>consumo_litros</code>) e depois pelos meses do ano.",
        ],
        "regras": ["Natureza de despesa 33903001 (Combustíveis e lubrificantes automotivos), processos da gerenciadora de frota (GOLDI, contrato 008/2019; PRIME, contrato 005/2024). Processo de compra de material de consumo é excluído.",
                   "Fósseis = diesel + gasolina; renováveis = etanol abastecido."],
        "confere": ["Extrato GOLDI: soma dos abastecimentos = total das faturas ao centavo (dez/2023 R$ 124.337,77; mai/2024 R$ 130.553,99).", "NF da PRIME de jun, jul e ago/2024: soma dos itens (litros × preço) = valor líquido pago no Portal (R$ 79.529,47, R$ 139.038,31 e R$ 165.435,57).",
                    "PRIME jan/2025: R$ 61.160,88, igual à planilha de gastos por posto do mesmo processo."],
        "limites": ["Jun, jul e ago/2024 não têm relatório de abastecimentos (só tickets em R$): os litros vêm da NF de serviço da PRIME (documento NOTA do processo), um total por combustível no mês, sem placa nem subunidade, atribuído ao Campus I.",
                    "A subunidade vem truncada em alguns relatórios de 2025 (“CAMPUS”): foi atribuída ao Campus I (postos quase todos em João Pessoa)."],
    },
    "residuos_kg": {
        "fontes": FONTES_FATURA,
        "passos": [
            *PASSOS_FATURA_COMUM,
            "Ler o relatório de fiscalização mensal da GMA/SINFRA: uma linha por campus com kg coletados, preço por kg e valor.",
            "Usar o período do assunto do processo no SIPAC (“serviços prestados no período de 01/02/2026 a 28/02/2026”) como mês de referência, porque a planilha às vezes repete o mês anterior.",
            *PASSOS_FATURA_FIM,
            "Somar os kg por mês e campus (métrica <code>residuos_kg</code>) e depois pelos meses do ano.",
        ],
        "regras": ["Natureza de despesa 33903978, só pagamentos à B-Green/Stericycle (contrato 009/2022 e aditivos), resíduos dos grupos A, B e E."],
        "confere": ["Fev/2026: 2.514,4 kg e R$ 13.753,77, iguais ao total da medição."],
        "limites": ["Campus IV não tem coleta contratada.",
                    "Nov/2025 cobre 01/11 a 19/12 (troca de aditivo): 2025 aparece com 11 meses, mas o total do ano está completo.",
                    "Não inclui resíduos comuns nem recicláveis (sem medição pública)."],
    },
    "co2e_kg": {
        "fontes": [("Viagens a serviço do Portal da Transparência (zip anual)", PORTAL_VIAGENS,
                    "viagens e trechos (origem, destino, meio de transporte) do órgão 26240"),
                   ("Programa Brasileiro GHG Protocol, ferramenta v2022.1.1", None, "fatores de emissão da aviação civil por faixa de distância")],
        "passos": [
            "Ler do zip anual as viagens da UFPB e os trechos, sem CPF, nome, cargo ou motivo (<code>viagens/load_viagens.py</code>).",
            "Localizar origem e destino de cada trecho aéreo pelas coordenadas dos municípios (base aberta de códigos IBGE) e calcular a distância de grande círculo × 1,08 (acréscimo DEFRA para a rota real).",
            "Multiplicar a distância pelo fator de emissão da faixa (kg CO2e por passageiro-km, tabela abaixo).",
            "Somar os kg CO2e pelo mês de início das viagens realizadas.",
        ],
        "regras": ["Só viagens com situação “Realizada” e trechos com meio de transporte aéreo."] + [
            f"Faixa {int(r.faixa_min_km)}–{int(r.faixa_max_km) if r.faixa_max_km < 99999 else '∞'} km: {str(r.kg_co2e_por_pkm).replace('.', ',')} kg CO2e/pkm"
            for r in fatores[fatores["meio"] == "aereo"].itertuples()],
        "confere": [],
        "limites": ["Trechos internacionais ficam sem distância (sem coordenadas no arquivo) e não entram.",
                    "Fatores da versão 2022.1.1 da ferramenta (última em link aberto); atualizar quando a nova versão for obtida."],
    },
    "pago": {"fontes": FONTES_DESPESA, "passos": PASSOS_DESPESA, "regras": [], "confere": CONFERE_DESPESA, "limites": LIMITE_DESPESA},
    "pago_acao": {
        "fontes": FONTES_DESPESA,
        "passos": [
            PASSOS_DESPESA[0],
            "Montar o mapa empenho → ação orçamentária com todos os arquivos diários em cache: o pagamento não traz a ação, só o empenho, e o arquivo do dia da emissão do empenho a informa (<code>despesas/load_despesas.acoes_por_empenho</code>).",
            "Para cada pagamento, pegar a ação do empenho impactado. Pagamentos da ação 4572 entram com qualquer natureza (diárias, passagens, instrutoria, auxílios, equipamentos), mesmo as que o painel não acompanha em outros temas.",
            "Somar por mês e elemento de despesa (métrica <code>pago_acao</code>), corrigir pelo IPCA e guardar o nominal.",
            PASSOS_DESPESA[4],
        ],
        "regras": [f"Ação {r.acao} – {r.nome}." for r in acoes.itertuples()],
        "confere": ["O pago da ação 4572 é independente da natureza: não pega o concurso público do IBFC (ação 20RK), que distorcia o indicador anterior."],
        "limites": LIMITE_DESPESA + ["Pagamento de empenho anterior a 2023 (restos a pagar antigos) fica sem ação e não entra: ≈ 9% dos pagamentos do período.",
                                      "Mostra o que foi orçado como capacitação: curso pago por outra ação entra no A6-CAPAC-02."],
    },
    "empenhado_itens": {
        "fontes": [("Arquivos diários de despesas do Portal da Transparência (itens de empenho)", PORTAL_DESPESAS,
                    "descrição, quantidade e valor de cada item das notas de empenho"), FONTES_DESPESA[1][:3]],
        "passos": [
            PASSOS_DESPESA[0],
            "Ler os itens das notas de empenho emitidas no dia (os itens de empenhos de outros dias são inscrição automática em restos a pagar e ficam de fora), só de naturezas acompanhadas pelo PLS.",
            "Normalizar a descrição (sem acento, minúsculas) e aplicar as regras de texto de <code>ref/regras_texto_pls.csv</code> (expressões regulares abaixo).",
            "Somar o valor dos itens que casaram a regra pelo mês de emissão do empenho (métrica <code>empenhado_itens</code>), corrigir pelo IPCA e guardar o nominal.",
            PASSOS_DESPESA[4],
        ],
        "regras": [],
        "confere": ["Itens lidos: 18.629 de 2024 a 2026."],
        "limites": ["É o valor empenhado (compra contratada), não o consumido nem o pago.",
                    "O Portal não traz a quantidade dos itens de ata (vem 0): não dá para contar unidades.",
                    "Regra de texto pode perder descrições fora do padrão ou pegar falsos positivos — revisar a lista de itens periodicamente."],
    },
}

FAMILIA_EVG = {
    "fontes": [("Cursos e participantes da Escola Virtual de Governo (ENAP, dados.gov.br)",
                "https://dados.gov.br/dados/conjuntos-dados/dados-sobre-cursos-e-participantes-na-plataforma-da-escola-virtual-de-governo-evg",
                "um CSV por bimestre com todas as matrículas do país (curso, temática, carga horária, situação, instituição declarada pelo aluno)")],
    "passos": [
        "Ler a lista de arquivos bimestrais em <code>ref/evg_recursos.csv</code> (ids do Google Drive da ENAP publicados no dados.gov.br).",
        "Baixar cada bimestre em streaming (50 a 360 MB, sem gravar o arquivo) e guardar só as matrículas cuja instituição declarada é “Universidade Federal da Paraíba” (<code>evg/load_evg.py</code>, cache em <code>data/raw/evg/</code>).",
        "LGPD: nome e CPF parcial (presentes até 2024) são descartados na leitura; fica só um código irreversível (hash com sal local) para contar pessoas distintas no ano. Desde 2025 a própria ENAP publica o código anonimizado.",
        "Juntar os bimestres, manter a extração mais recente de cada matrícula, datar pela matrícula e marcar: concluída (situação “Concluída”) e sustentabilidade (palavras-chave de <code>ref/evg_sustentabilidade.csv</code> no nome do curso; a temática da ENAP não é usada porque classifica como “Meio Ambiente” cursos alheios à gestão sustentável).",
        "Somar por mês (<code>indicadores/build_indicadores.py</code>): matrículas, certificações (concluídas), horas certificadas e pessoas certificadas em sustentabilidade (cada pessoa só no mês da primeira certificação do ano).",
        "Somar os meses do ano (<code>metas/load_metas.py</code>); ano com menos de 12 meses de matrícula nos arquivos fica parcial.",
    ],
    "regras": ["Instituição declarada = “Universidade Federal da Paraíba” (lista padronizada da EVG; comparação sem acento e sem diferenciar maiúsculas).",
               "Certificação = matrícula com situação “Concluída” no arquivo mais recente em que aparece."],
    "confere": ["Nov–dez/2025, lido direto do arquivo da ENAP na análise da base: 633 matrículas da UFPB, 208 pessoas, 407 concluídas, 9.221 horas — os mesmos números saem do módulo.", "Arquivo mai–jun/2023 começa com marca BOM e nov–dez/2024 vem sem cabeçalho: o leitor trata os dois (testado)."],
    "limites": ["A instituição é declarada pelo aluno (experiência profissional mais recente): não confirma vínculo de servidor, pode incluir estudante, terceirizado ou ex-servidor, e quem não preenche o campo fica de fora.",
                "Só cursos da EVG: capacitações da PROGEP, de outras escolas de governo e presenciais não entram.",
                "Situação da matrícula na data de extração do bimestre: matrícula feita no fim do período pode concluir depois e aparecer como não concluída.",
                "Meses que faltam nos próprios arquivos da ENAP: set/2023 (o bimestre set–out só traz outubro), dez/2024 (nov–dez só traz novembro, com cada linha duplicada) e abr/2026 (mar–abr só traz março) — 2023 e 2024 ficam marcados como parciais.",
                "Salto em 2025 (de ≈ 1.800 para ≈ 6.000 matrículas da UFPB no ano) aparece em todos os bimestres: pode refletir mais cursos feitos ou mais alunos preenchendo a instituição no cadastro — não dá para separar os dois efeitos.",
                "O dado exato (servidores e cursos concluídos, com CPF) está no SIGRH/PROGEP e permitiria confirmar o vínculo."],
}
FAMILIAS["emissoes_kgco2e"] = {
    "fontes": FONTES_FATURA + [("Viagens a serviço do Portal da Transparência", PORTAL_VIAGENS, "trechos aéreos das viagens realizadas"),
                               ("Fatores de emissão da energia elétrica do SIN (MCTI/SIRENE, planilha Inventários Corporativos)", "https://www.gov.br/mcti/pt-br/acompanhe-o-mcti/sirene/dados-e-ferramentas/fatores-de-emissao", "fator médio mensal de CO₂ (tCO₂/MWh) de 2006 até o último mês publicado; lido todo mês pelo módulo fator_sin"),
                               ("Fatores de emissão dos combustíveis", None, "IPCC 2006 (combustíveis) e misturas obrigatórias de biocombustível (CNPE), em ref/fatores_gee.csv")],
    "passos": [
        "Partir do que o painel já mede por mês: litros por combustível (relatórios de abastecimento), kWh da rede (faturas da Energisa) e kg CO₂e das viagens aéreas.",
        "Escopo 1 (frota): litros × fator de CO₂ do combustível fóssil, descontada a parte de biocombustível da mistura obrigatória do mês (biodiesel no diesel, etanol anidro na gasolina). Etanol hidratado não entra: o CO₂ é biogênico.",
        "Escopo 2 (energia): kWh consumido da rede no mês × fator médio do SIN do mesmo mês, publicado pelo MCTI (módulo <code>fator_sin</code>, que acha na página do SIRENE o link da planilha “Inventários Corporativos” e lê os fatores mensais). Mês ainda não publicado usa o fator anual do último ano fechado e é marcado como provisório.",
        "Escopo 3 (viagens aéreas): distância dos trechos × fator por faixa de distância (GHG Protocol).",
        "Somar por mês e escopo (métrica <code>emissoes_kgco2e</code>, <code>indicadores/build_indicadores.py</code>) e depois pelos meses do ano.",
    ],
    "regras": [f"{e(r.item)} ({e(r.inicio)} a {e(r.fim)}): {str(r.valor).replace('.', ',')} {e(r.unidade)}. Fonte: {e(r.fonte)}."
               for r in pd.read_csv(ETL / "ref" / "fatores_gee.csv", sep=";", dtype=str).itertuples()],
    "confere": ["Os consumos de origem (litros, kWh, trechos) têm as conferências das suas próprias fichas.", "A média dos fatores mensais lidos bate com o fator anual publicado pelo MCTI: 0,0385 (2023), 0,0545 (2024) e 0,0461 (2025) tCO₂/MWh."],
    "limites": ["O MCTI publica o fator mensal com um a três meses de atraso: os últimos meses do ano em curso ficam provisórios até a planilha nova sair (a verificação da carga avisa).",
                "Só CO₂ na frota e na energia (CH₄ e N₂O da combustão móvel ficam de fora, menos de 2% do total).",
                "Resíduos, efluentes e gases refrigerantes ainda fora do inventário."],
}
FAMILIAS["empenhado_material_consumo"] = {
    "fontes": FAMILIAS["empenhado_itens"]["fontes"],
    "passos": FAMILIAS["empenhado_itens"]["passos"][:3] + [
        "Separar os itens de material de consumo (natureza 3.3.90.30) em “com atributo sustentável” (regra item_sustentavel) e “demais itens”.",
        "Percentual = valor dos itens com atributo ÷ valor de todo o material de consumo empenhado no ano."],
    "regras": ["Natureza de despesa começando por 3.3.90.30 (material de consumo)."],
    "confere": FAMILIAS["empenhado_itens"]["confere"],
    "limites": FAMILIAS["empenhado_itens"]["limites"],
}
FAMILIAS["evg_certificados"] = FAMILIA_EVG
FAMILIAS["evg_pessoas_sust"] = FAMILIA_EVG

PNCP = "https://pncp.gov.br/app/editais"
COMPRAS_GOV = "https://dadosabertos.compras.gov.br/swagger-ui/index.html"
_crit = pd.read_csv(ETL / "ref" / "criterios_editais.csv", sep=";", dtype=str, keep_default_na=False)
FONTES_PNCP = [
    ("Contratações da UFPB no Compras.gov.br (dados abertos, módulo contratações PNCP 14.133)", COMPRAS_GOV,
     "lista das contratações publicadas no PNCP pelo CNPJ da UFPB, com modalidade, registro de preços, objeto e valores estimado e homologado"),
    ("Portal Nacional de Contratações Públicas (PNCP)", PNCP,
     "documentos de cada compra (edital, termo de referência, estudo técnico preliminar, aviso de contratação direta) e itens (margem de preferência, benefício ME/EPP)"),
]
FAMILIAS["contratacoes_pncp"] = {
    "fontes": FONTES_PNCP,
    "passos": [
        "Listar as contratações da UFPB publicadas no PNCP no ano, em todas as modalidades (<code>compras/load_compras.py</code>).",
        "Para licitações e dispensas, baixar do PNCP o edital, o termo de referência, o ETP e o aviso de contratação direta e extrair o texto de cada página (PDF, ZIP, DOCX). Inexigibilidades (assinaturas, cursos, credenciamentos) não têm documentos lidos.",
        "Marcar cada página como ETP ou TR/edital pelo cabeçalho do Compras.gov.br (“UASG 153065 Termo de Referência 41/2024”). A UFPB costuma publicar os três num PDF só.",
        "Procurar os critérios de <code>ref/criterios_editais.csv</code> no texto sem acentos. Critério concreto fora do ETP → “critério específico”; se o critério só aparece em frase de preferência (“preferencialmente”, “priorizar”) → “só cláusula de preferência”. Só menção a “critérios de sustentabilidade”, IN 01/2010, Guia da AGU ou PNRS → “só menção genérica”. Nada → “sem critério”.",
        "Contar por mês de publicação no PNCP e nível (métrica <code>contratacoes_pncp</code>) e somar o valor homologado (ou estimado, se não houver) em <code>contratacoes_pncp_valor</code>.",
        "Percentual = contratações com critério específico / contratações com documento legível, em licitações e dispensas.",
    ],
    "regras": [f"{e(r.descricao)}: <code>{e(r.padrao)}</code>" for r in _crit[_crit["marcador"] == "sustentabilidade"].itertuples()],
    "confere": ["Cada contratação guarda os trechos que casaram (até 6), para conferência por amostra no painel e no parquet pls_compras."],
    "limites": ["O modelo de TR da AGU já traz a seção “Sustentabilidade” com texto padrão; por isso só a menção não conta. Critério concreto em frase de preferência (“preferencialmente”, “priorizar”, “sempre que possível”) fica no nível “só cláusula de preferência”, fora do numerador, porque não obriga o fornecedor.",
                "PDF escaneado não tem texto: a contratação fica “sem documento legível” e sai da razão.",
                "Critério que está só no item (descrição do catálogo) e não no texto do edital/TR não é detectado."],
}
FAMILIAS["contratacoes_pncp_valor"] = FAMILIAS["contratacoes_pncp"]
FAMILIAS["editais_marcadores"] = {
    "fontes": FONTES_PNCP,
    "passos": [
        "Mesma leitura de documentos do N10.",
        "Universo pelo objeto da contratação: dedicação exclusiva de mão de obra, alimentos (refeições, RU, gêneros alimentícios) ou obra e projeto de engenharia.",
        "Critério pelo texto do edital/TR, fora do ETP: cota para mulheres vítimas de violência (Decreto 11.430/2023), mão de obra local, agricultura familiar, BIM.",
        "Margem de preferência pelos itens da licitação no PNCP (campos de margem normal e adicional).",
        "Contar por mês de publicação e “universo · com/sem critério” (métrica <code>editais_marcadores</code>). Percentual = com / (com + sem).",
    ],
    "regras": [f"{e(r.marcador)} ({e(r.onde)}): {e(r.descricao)}" for r in _crit[_crit["marcador"] != "sustentabilidade"].itertuples()],
    "confere": ["Os editais marcados podem ser abertos pelo link do PNCP de cada contratação em pls_compras."],
    "limites": ["O universo vem do objeto, que às vezes usa o texto padrão do sistema (“obras ou serviços de engenharia… dedicação exclusiva”) para serviços que não são obra; a regra de obra ignora esse texto padrão.",
                "Agricultura familiar: mede se o edital prevê a compra, não se atinge os 30% do E5-AGRIC-01."],
}
FAMILIAS["compras_compartilhadas"] = {
    "fontes": [FONTES_PNCP[0], ("Atas de registro de preços (Compras.gov.br, módulo ARP)", COMPRAS_GOV,
                                "itens das atas das UASGs da UFPB, unidades participantes de cada item e adesões"),
               ("Contratos e empenhos da UFPB no PNCP", PNCP, "compra de origem de cada contrato e indicação de adesão")],
    "passos": [
        "Para cada ata de registro de preços das UASGs da UFPB com vigência iniciada no ano, consultar as unidades de cada item. Unidade participante de outro órgão → “IRP da UFPB com participante externo”.",
        "Quando o saldo de adesões de um item é menor que o limite, consultar as adesões. Adesão de unidade de outro órgão → “Ata da UFPB com adesão de outro órgão”.",
        "Nos contratos e empenhos da UFPB no PNCP, a compra de origem com CNPJ de outro órgão indica participação da UFPB em compra alheia; com o indicador de adesão, adesão (carona).",
        "Contar cada compra uma vez por tipo, no mês da assinatura da ata ou do primeiro contrato (métrica <code>compras_compartilhadas</code>).",
    ],
    "regras": ["UASGs da UFPB (153065, 153066, 153073, 153074) não contam como órgão externo."],
    "confere": ["Cada compra compartilhada guarda a referência da ata ou da compra e as unidades envolvidas (pls_compras_compartilhadas)."],
    "limites": ["Contratos e empenhos antigos (Lei 8.666) não estão no PNCP: a participação da UFPB em compras de outros órgãos só aparece a partir das publicações no PNCP.",
                "Para economizar consultas, cada ata para no primeiro participante e na primeira adesão encontrados."],
}

_forn = ETL / "data" / "processed" / "pls_fornecedores.parquet"
_forn = pd.read_parquet(_forn) if _forn.exists() else pd.DataFrame()
_cad = ETL / "data" / "raw" / "cnpj" / "cadastro.json"
_mes_cad = __import__("json").loads(_cad.read_text(encoding="utf-8")).get("mes", "") if _cad.exists() else ""
FAMILIAS["pago_fornecedores"] = {
    "fontes": FONTES_DESPESA[:1] + [
        ("Cadastro Nacional da Pessoa Jurídica, dados abertos da Receita Federal",
         "https://arquivos.receitafederal.gov.br/",
         f"arquivos Empresas (porte), Estabelecimentos (UF e município de cada CNPJ) e Simples (opção e datas), pasta {_mes_cad or 'mais recente'}; lidos em fluxo e filtrados pelos CNPJ pagos pela UFPB"),
    ],
    "passos": [
        "Do cache diário de despesas, pegar todos os pagamentos (pago + restos a pagar pagos) a favorecido com CNPJ, em aplicação direta (modalidade 90) e nos elementos de contratação 30, 32, 33, 35, 37, 39, 40, 51 e 52 (<code>cnpj/load_cnpj.py</code>). Entram também as naturezas que não são temas do PLS: o denominador é toda a contratação da UFPB.",
        "Baixar os arquivos do cadastro de CNPJ da Receita (~7 GB), um zip por vez, e guardar só as linhas dos CNPJ pagos: porte da empresa (raiz de 8 dígitos) e UF do estabelecimento que recebeu (CNPJ de 14 dígitos).",
        "Classificar cada pagamento: ME/EPP (porte 01 ou 03) ou demais portes × sede na Paraíba ou em outro estado; empenho com amparo da Lei 12.512/2011, 11.947/2009 ou 14.628/2023 vira “Agricultura familiar”; banco (CNAE 64) vira “Instituição financeira”; CNPJ fora do cadastro vira “Sem cadastro na Receita”.",
        "Somar por mês e categoria (métrica <code>pago_fornecedores</code>) e depois pelos meses do ano.",
        "Percentual = pago às categorias do numerador ÷ pago a todas as categorias, exceto instituição financeira.",
    ],
    "regras": ["ME/EPP: porte 01 (microempresa) ou 03 (empresa de pequeno porte) no cadastro da Receita.",
               "Paraíba: UF do estabelecimento (CNPJ completo) que recebeu o pagamento.",
               "Instituição financeira: CNAE principal começando por 64. São depósitos em conta vinculada de terceirizadas e arrecadação de faturas: o beneficiário real é outro, então ficam fora da razão."]
              + ([f"Cadastro lido: {len(_forn)} CNPJ pagos, {int(_forn['no_cadastro'].sum())} encontrados na Receita, "
                  f"{int(_forn['me_epp'].sum())} ME/EPP e {int(_forn['sede_local'].sum())} com estabelecimento na Paraíba."] if not _forn.empty else []),
    "confere": ["O total pago a PJ nas naturezas de contratação é a mesma soma de pago + RP pago que, nos temas do PLS, bate ao centavo com as Tabelas 10, 12 e 13 do PLS."],
    "limites": ["Porte e UF são os do cadastro na data da extração, não os da data do pagamento: empresa que cresceu ou mudou de sede é classificada pelo estado atual. O Simples/MEI traz as datas de opção e exclusão, guardadas para conferência.",
                "Nenhum empenho de 2023 a 2026 cita a Lei 12.512/2011 (PAA), a 11.947/2009 ou a 14.628/2023, então a agricultura familiar fica em zero. Compras de agricultura familiar sob outro amparo não seriam reconhecidas.",
                "Fornecedor novo aparece como “Sem cadastro” até a próxima releitura da Receita (a cada 90 dias)."],
}


def _selecao(calc: dict) -> pd.DataFrame:
    s = ind[ind["metrica"] == calc["metrica"]]
    if calc["tema"]:
        s = s[s["tema_codigo"] == calc["tema"]]
    if calc["subtemas"]:
        s = s[s["subtema"].isin(calc["subtemas"])]
    return s


def _regras_especificas(r, calc) -> list[str]:
    out = []
    subs = calc["subtemas"] or []
    if calc["metrica"] == "pago":
        m = mapa[mapa["subtema"].isin(subs) | ((mapa["tema_codigo"] == (calc["tema"] or "")) & (calc["tema"] is not None))]
        for x in m.itertuples():
            out.append(f"Natureza <code>{e(x.natureza)}</code> – {e(x.descricao_natureza)} → subtema “{e(x.subtema)}”.")
        if "Treinamento (outras ações)" in subs:
            out.append("Natureza <code>33903948</code> dividida em três subtemas: “Concurso e seleção” (observação ou favorecido com concurso público, processo seletivo, vestibular ou organizadora de concurso — IBFC, Cebraspe, FGV, Idecan, Fundatec, Vunesp, Cesgranrio, AOCP, Comperve, Quadrix, Consulplan), “Serviços de treinamento (ação 4572)” e “Treinamento (outras ações)”. Só o último entra aqui.")
    if calc["metrica"] == "empenhado_itens":
        for sub in subs or regras[regras["tema_codigo"] == calc["tema"]].index:
            if sub in regras.index:
                out.append(f"Regra “{e(sub)}”: <code>{e(regras.loc[sub, 'padrao'])}</code>")
    if calc.get("razao_subtemas"):
        out.append(f"Percentual = {', '.join(subs)} ÷ ({' + '.join(calc['razao_subtemas'])}) × 100.")
    if calc["campo"] == "valor_real_per_capita":
        out.append("Divisão pela comunidade acadêmica da UFPB no ano: discentes + docentes + técnicos-administrativos + terceirizados (<code>ref/comunidade_ufpb.csv</code>). Ano sem contagem usa o último disponível; ano fora da planilha usa o Censo INEP.")
    if calc["campo"] == "pct_servidores":
        out.append("Divisão pelo total de servidores: docentes + técnicos-administrativos da contagem da UFPB do ano (ou o último disponível), sem terceirizados, × 100.")
    if calc["metrica"] == "evg_pessoas_sust":
        regras_evg = pd.read_csv(ETL / "ref" / "evg_sustentabilidade.csv", sep=";", dtype=str)
        for x in regras_evg.itertuples():
            out.append(f"Curso de sustentabilidade pelo campo <code>{e(x.campo)}</code>: <code>{e(x.padrao)}</code>")
        evg = pd.read_parquet(PROC / "pls_evg.parquet") if (PROC / "pls_evg.parquet").exists() else pd.DataFrame()
        if not evg.empty:
            cursos = evg[evg["sustentabilidade"] & evg["concluida"]]["nome_curso"].value_counts().head(25)
            out.append("Cursos que casaram a regra (certificações da UFPB, 25 mais frequentes): " + "; ".join(f"{e(k)} ({v})" for k, v in cursos.items()) + ".")
    if calc["campo"] == "valor_por_m2":
        out.append(f"Divisão pela área construída informada pela UFPB (<code>ref/area_construida.csv</code>): {num(area['area_m2'].sum(), 'm²')} no total; recorte por campus usa a área do campus. Razão das somas, não soma das razões.")
    return out


def _tabela_calculo(r, calc) -> str:
    unidade = r.unidade
    rs = unidade.startswith("R$")
    sel = _selecao(calc)
    meses = _meses_carregados(calc["metrica"])
    m = metas[metas["indicador_id"] == r.id].set_index("ano")
    linhas = []
    for a in ANOS:
        s = sel[sel["ano"] == a]
        nom, real = s["valor_nominal"].sum(), s["valor_real"].sum()
        unid_num = "R$" if rs else {"consumo_kwh": "kWh", "consumo_m3": "m³", "consumo_litros": "L", "residuos_kg": "kg", "co2e_kg": "kg CO2e", "emissoes_kgco2e": "kg CO2e", "evg_certificados": "certificados", "evg_pessoas_sust": "pessoas"}.get(calc["metrica"], "")
        numer = num(nom, unid_num) + (f"<small>corrigido {num(real, unid_num)}</small>" if rs else "")
        if calc["campo"] == "valor_real_per_capita":
            ano_c = max([c for c in COMUNIDADE.index if c <= a], default=None)
            den = (f"{num(COMUNIDADE.loc[ano_c, 'comunidade'], 'pessoas')}<small>{e(COMUNIDADE.loc[ano_c, 'fonte'])} {ano_c}</small>"
                   if ano_c else "—")
        elif calc["campo"] == "pct_servidores":
            srv = s["servidores"].max() if len(s) else float("nan")
            den = f"{num(srv, 'servidores')}<small>docentes + técnicos (UFPB)</small>"
        elif calc["campo"] == "valor_por_m2":
            den = num(s.drop_duplicates("area_m2")["area_m2"].sum(), "m²")
        elif calc.get("razao_subtemas"):
            t = ind[(ind["metrica"] == calc["metrica"]) & ind["subtema"].isin(calc["razao_subtemas"]) & (ind["ano"] == a)]["valor_nominal"].sum()
            den = num(t, "L")
        else:
            den = "—"
        res = m.loc[a] if a in m.index else None
        resultado = num(res["valor"], unidade) if res is not None else "—"
        sit = res["situacao"].replace("_", " ") if res is not None else ""
        var = res["variacao_pct"] if res is not None else float("nan")
        var_txt = f"{var:+.1f}%".replace(".", ",") if isinstance(var, float) and not math.isnan(var) else ""
        linhas.append(f'<tr><th scope="row">{a}<small>{meses.get(a, 0)} meses</small></th><td class="r">{numer}</td>'
                      f'<td class="r">{den}</td><td class="r"><b>{resultado}</b><small>{e(sit)} {var_txt}</small></td></tr>')
    den_rot = {"valor_real_per_capita": "Denominador (pessoas)", "valor_por_m2": "Denominador (área)",
               "pct_servidores": "Denominador (servidores)"}.get(calc["campo"], "Denominador")
    if calc.get("razao_subtemas"):
        den_rot = "Denominador (litros totais)"
    nota = f"<p class='nota'>R$ corrigidos pelo IPCA para {REF_IPCA_TXT}; o nominal é a soma como foi pago.</p>" if rs else ""
    return (f'<div class="tab"><table><thead><tr><th>Ano</th><th class="r">Numerador</th><th class="r">{den_rot}</th>'
            f'<th class="r">Resultado</th></tr></thead><tbody>{"".join(linhas)}</tbody></table></div>{nota}')


def lista(itens) -> str:
    return "<ul>" + "".join(f"<li>{i}</li>" for i in itens) + "</ul>" if itens else "<p class='nota'>—</p>"


def secao_auto(r) -> str:
    calc = catalogo.parse_calculo(r.calculo)
    fam = FAMILIAS[calc["metrica"]]
    fontes = list(fam["fontes"])
    if calc["campo"] == "valor_real_per_capita":
        fontes.append(("Contagem da comunidade acadêmica da UFPB", None, "discentes, docentes, técnicos-administrativos e terceirizados por ano"))
        fontes.append(("Censo da Educação Superior (INEP, microdados)", INEP, "reserva para ano fora da contagem da UFPB (código 579)"))
    fontes_html = "<ul>" + "".join(fonte(*f) for f in fontes) + "</ul>"
    passos = "<ol>" + "".join(f"<li>{p}</li>" for p in fam["passos"]) + "</ol>"
    regras_html = lista(fam["regras"] + _regras_especificas(r, calc))
    limites = list(fam["limites"])
    if r.confirmar and not any(r.confirmar in l for l in limites):
        limites.append("<b>A confirmar pela Comissão:</b> " + e(r.confirmar))
    return (
        f'<section class="ind" id="{e(r.id)}"><header><span class="id">{e(r.id)}</span>'
        f'<span class="tag auto">Automatizado</span><span class="orig">{origem(r)}</span></header>'
        f'<h3>{e(r.indicador)}</h3><p class="obj">{e(r.objetivo)}</p>'
        f'<dl class="ficha"><div><dt>Fórmula</dt><dd><code>{e(r.formula)}</code></dd></div>'
        f'<div><dt>Unidade</dt><dd>{e(r.unidade)}</dd></div><div><dt>Meta</dt><dd>{e(r.meta or "—")}</dd></div>'
        f'<div><dt>Responsável no PLS</dt><dd>{e(r.responsavel)}</dd></div>'
        f'<div><dt>Regra de cálculo no ETL</dt><dd><code>{e(r.calculo)}</code></dd></div></dl>'
        f'<h4>1. Fontes</h4>{fontes_html}<h4>2. Construção passo a passo</h4>{passos}'
        f'<h4>3. Regras e filtros</h4>{regras_html}<h4>4. Cálculo ano a ano</h4>{_tabela_calculo(r, calc)}'
        f'<h4>5. Conferências</h4>{lista(fam["confere"])}<h4>6. Limitações</h4>{lista(limites)}</section>'
    )


NIVEL = {("integracao", "publica"): "Integrar dado público", ("integracao", "fornecedor"): "Integrar dado do fornecedor",
         ("integracao", "interna"): "Integrar sistema da UFPB", ("informado", "documental"): "Informado pela Comissão"}


def origem(r) -> str:
    return f"PLS · Tabela {e(r.tabela_pls)}" if r.id.startswith("E") and r.tabela_pls else "Ampliação do painel"


def secao_pend(r) -> str:
    rot = NIVEL.get((r.automacao, r.tipo_fonte), "Informado pela Comissão")
    conf = f"<div><dt>A confirmar</dt><dd>{e(r.confirmar)}</dd></div>" if r.confirmar else ""
    return (
        f'<section class="ind pend" id="{e(r.id)}"><header><span class="id">{e(r.id)}</span>'
        f'<span class="tag pend">{e(rot)}</span><span class="orig">{origem(r)}</span></header>'
        f'<h3>{e(r.indicador)}</h3><p class="obj">{e(r.objetivo)}</p>'
        f'<dl class="ficha"><div><dt>Fórmula</dt><dd><code>{e(r.formula)}</code></dd></div>'
        f'<div><dt>Unidade</dt><dd>{e(r.unidade)}</dd></div><div><dt>Meta</dt><dd>{e(r.meta or "—")}</dd></div>'
        f'<div><dt>Responsável no PLS</dt><dd>{e(r.responsavel)}</dd></div>'
        f'<div><dt>Dado hoje</dt><dd>{e(r.fonte_hoje or "Não há")}</dd></div>'
        f'<div><dt>Construção proposta</dt><dd>{e(r.rota_automacao)}</dd></div>{conf}</dl>'
        f'<p class="nota">Ainda sem construção automática: até a integração existir, o valor anual é lançado pela Comissão em '
        f'<code>data/metas/valores_informados.csv</code> com fonte, responsável e data.</p></section>'
    )


def montar() -> str:
    corpo, sumario = [], []
    for eixo in sorted(cat["eixo_pls"].unique(), key=int):
        sub = cat[cat["eixo_pls"] == eixo]
        sub = pd.concat([sub[sub["automacao"] == "automatico"], sub[sub["automacao"] != "automatico"]])
        corpo.append(f'<h2 id="eixo-{eixo}"><span>Eixo {eixo}</span> {e(eixos[eixo])}</h2>')
        itens = []
        for r in sub.itertuples():
            auto = r.automacao == "automatico"
            corpo.append(secao_auto(r) if auto else secao_pend(r))
            itens.append(f'<li class="{"a" if auto else "p"}"><a href="#{e(r.id)}"><span>{e(r.id)}</span> {e(r.indicador)}</a></li>')
        sumario.append(f'<li><a href="#eixo-{eixo}" class="ex">Eixo {eixo} · {e(eixos[eixo])}</a><ul>{"".join(itens)}</ul></li>')
    return "".join(corpo), "".join(sumario)


def correcoes_html() -> str:
    return "".join(f"<tr><td><code>{e(r.processo_portal)}</code></td><td><code>{e(r.processo_sipac)}</code></td><td>{e(r.evidencia)}</td></tr>"
                   for r in corrigidos.itertuples())


def main() -> None:
    corpo, sumario = montar()
    auto = int((cat["automacao"] == "automatico").sum())
    ok = faturas.drop_duplicates("processo")
    TEMPLATE = Path(__file__).with_name("construcao_template.html").read_text(encoding="utf-8")
    pagina = (TEMPLATE.replace("{{CORPO}}", corpo).replace("{{SUMARIO}}", sumario)
              .replace("{{N}}", str(len(cat))).replace("{{N_AUTO}}", str(auto)).replace("{{N_PEND}}", str(len(cat) - auto))
              .replace("{{PROC_OK}}", str(int((ok["status"] == "ok").sum()))).replace("{{PROC_N}}", str(len(ok)))
              .replace("{{CORRECOES}}", correcoes_html()).replace("{{REF_IPCA}}", REF_IPCA_TXT)
              .replace("{{DATA}}", date.today().strftime("%d/%m/%Y")))
    assert "{{" not in pagina
    OUT.write_text(pagina, encoding="utf-8")
    print(OUT, len(cat), auto)


if __name__ == "__main__":
    main()
