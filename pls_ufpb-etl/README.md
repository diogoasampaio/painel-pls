# pls_ufpb-etl

ETL do Painel de Sustentabilidade (PLS) da UFPB. Extrai dados públicos, classifica
nos temas e eixos do PLS UFPB 2025–2029 (Portaria SEGES/ME 8.678/2021, art. 7º) e
grava no MongoDB `painel_pls`, uma coleção por fonte, mais as coleções derivadas
`pls_indicadores` (séries mensais) e `pls_metas` (indicadores do plano × meta) que a
API lê.

## Módulos

| Módulo | Fonte | Coleções | Chave de substituição | Modo |
|---|---|---|---|---|
| `referencias` | `ref/*.csv` (mapeamento PLS) | `pls_eixos`, `pls_temas`, `pls_mapeamento`, `pls_regras_texto`, `pls_catalogo_indicadores` | coleção inteira | automático (mensal) |
| `despesas` | Portal: arquivos diários de despesas (dados abertos) + API só para os dias ainda não publicados | `pls_despesas`, `pls_empenhos`, `pls_itens_empenho` | `periodo` (AAAA-MM) | automático (mensal) |
| `faturas` | Processos de pagamento de energia, água, combustível e resíduos (do cache de `despesas`) → consulta pública do SIPAC → PDF (Energisa, CAGEPA, gerenciadora de frota, medição da B-Green) | `pls_faturas` | `processo` | automático (mensal) |
| `compras` | Contratações da UFPB no PNCP (lista no Compras.gov.br, edital/TR/itens no PNCP), atas de registro de preços (participantes e adesões) e contratos da UFPB ligados a compras de outros órgãos | `pls_compras`, `pls_compras_compartilhadas` | `ano` | automático (mensal; PNCP a 20 chamadas/min) |
| `cnpj` | Pagamentos a PJ em naturezas de contratação (de todo o cache de `despesas`) × cadastro aberto de CNPJ da Receita (porte, UF, Simples) | `pls_pagamentos_pj`, `pls_fornecedores` | `periodo` / `cnpj_basico` | automático (mensal; só baixa a Receita quando aparece fornecedor novo) |
| `evg` | Cursos e participantes da Escola Virtual de Governo (ENAP, dados.gov.br): CSVs bimestrais lidos em streaming, só matrículas com a UFPB declarada | `pls_evg` | `periodo` | automático (bimestral; atualizar `ref/evg_recursos.csv`) |
| `acoes` | Plano de ações do PLS UFPB (`ref/acoes_pls_ufpb.csv`) × acompanhamento semestral dos responsáveis (`data/metas/acompanhamento_acoes.csv`) | `pls_acoes` | coleção inteira | automático (situação contra o prazo) + informado (semestral) |
| `viagens` | Portal: download anual de Viagens (CSV) | `pls_viagens`, `pls_trechos` | `ano` | automático (mensal) |
| `ipca` | BCB/SGS série 433 | `pls_ipca` | `periodo` | automático (mensal) |
| `inep` | INEP: microdados do Censo da Educação Superior (reserva da contagem da UFPB) | `pls_comunidade` | `ano` | **manual** (anual, quando o censo sai) |
| `python -m common.comunidade <planilha.xlsx>` | Contagem da comunidade acadêmica da UFPB: discentes, docentes, técnicos e terceirizados por ano | `ref/comunidade_ufpb.csv` | `ano` | **manual** (anual, quando a planilha chega) |
| `formularios` | Envios dos setores pelo painel (`pls_form_acompanhamento`, `pls_form_valores`, gravados pela API) | CSVs de `data/metas/` | chave de cada linha | automático (diário e mensal) |
| `execucao` | `pls_metas` + `pls_acoes` + `ref/nucleo_pls.csv`, `ref/faixas_execucao.csv`, `ref/indice_execucao.csv` | `pls_execucao` | `conjunto` | automático (diário e mensal) |
| `saude` | `data/processed/*.parquet` + `ref/` + falhas da carga | `pls_saude_carga` | `execucao` | automático (fim da carga mensal) + e-mail |
| `indicadores` | `data/processed/*.parquet` dos módulos acima | `pls_indicadores` | `periodo` | automático |
| `metas` | `ref/indicadores_pls.csv` + `pls_indicadores` + `data/metas/valores_informados.csv` | `pls_metas` | coleção inteira | automático, sempre por último |

```
python run.py <modulo> [--inicio AAAA-MM] [--fim AAAA-MM] [--dry-run] [--so-arquivos]
python run.py mensal                     # referencias, ipca, despesas, faturas, viagens, indicadores, metas
```

- Sem `--inicio`/`--fim`, a janela são os **dois últimos meses fechados**. O Portal publica com atraso, então o mês anterior é sempre reprocessado.
- `--dry-run` processa e imprime os totais sem gravar nada.
- `--so-arquivos` grava só `data/processed/*.parquet`, sem Mongo. Serve para máquina local sem banco ou para ligar o Power BI direto nos parquet.
- `despesas --offline` usa só o cache bruto (arquivos e API), sem rede.

## Camadas em disco

```
data/raw/         resposta bruta de cada fonte (auditoria + cache para retomar carga)
  portal_bulk/<ano>/<dia>.json          linhas da UFPB do arquivo diário de despesas
  portal/documentos/<ug>/<fase>/<ano>/<dia>.json   (API, só dias sem arquivo)
  portal/itens_empenho/<ano>/<NE>.json
  portal/empenhos_impactados/<fase>/<ano>/<documento>.json
  inep/<ano>.json  bcb/ipca_sgs433.json  referencias/municipios.csv
data/processed/   um parquet por coleção (o que vai para o Mongo)
data/validacao/   exportações do Tesouro Gerencial para conferência (opcional)
```

## Instalação

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows  (Linux: source .venv/bin/activate)
pip install -r requirements.txt  # testes: requirements-dev.txt
copy .env.example .env           # preencher PORTAL_API_KEY e MONGO_URI
python -m pytest
```

A chave da API do Portal é gratuita e **opcional**: só cobre os dias recentes cujo
arquivo diário ainda não saiu. Sem ela, esses dias ficam de fora e o mês não é
gravado até a próxima execução. Cadastro em
<https://portaldatransparencia.gov.br/api-de-dados/cadastrar-email> (login gov.br).

## Carga histórica (primeira vez)

```bash
python run.py referencias
python run.py ipca
python run.py inep --inicio 2019-01 --fim 2024-12      # ~450 MB lidos por ano, via streaming
python run.py viagens --inicio 2019-01 --fim 2026-12
python run.py despesas --inicio 2019-01 --fim 2019-12 --dry-run   # confira os totais
python run.py despesas --inicio 2019-01 --fim 2019-12
# ... repetir despesas ano a ano ...
python run.py indicadores
```

**Custo da carga de despesas.** Um arquivo por dia (~5–30 MB, governo federal
inteiro). Do arquivo, só as linhas da UFPB vão para `data/raw/portal_bulk/`: um mês
ocupa ~3 MB. O servidor da CGU **bloqueia o IP (HTTP 405) depois de ~25 downloads
seguidos**. Por isso o ritmo padrão é de 4 arquivos por minuto (um ano leva ~1h30).
Ao ser bloqueado, o ETL pausa 15 min e tenta de novo; se o bloqueio continuar, para
de baixar e segue com o que tem. O mês com dias faltando **não é gravado**, e a
próxima execução retoma de onde parou.

## Mapeamento PLS: `ref/`

| Arquivo | Conteúdo |
|---|---|
| `eixos_pls.csv` | Os 6 eixos do PLS UFPB 2025–2029. |
| `temas_pls.csv` | Temas operacionais do painel (energia, água, frota...), cada um ligado a um eixo (`eixo_pls`), com rótulo e ordem. A API e o frontend leem daqui. |
| `indicadores_pls.csv` | Catálogo de indicadores: os 34 do plano (tabelas 16 a 24, ids `E1..E6`) e as ampliações do painel (ids `A*`), com meta, tipo de meta, nível de automação e rota de automação. Ver seção Metas. |
| `acoes_pls.csv` | Ações orçamentárias acompanhadas pelo PLS. Todos os pagamentos da ação entram na métrica `pago_acao`, com qualquer natureza. A ação vem do empenho impactado (mapa montado com todo o cache de arquivos diários). Hoje: 4572, capacitação de servidores (A6-CAPAC-01). |
| `processos_corrigidos.csv` | Números de processo gravados com erro no Portal, conferidos no SIPAC, com a evidência. |
| `area_construida.csv` | Área construída (m²) por campus e unidade. Denominador de kWh/m², m³/m² e R$/m²: área do campus no consumo das faturas, da UFPB inteira nas despesas. Uma fotografia só, aplicada a todos os anos; atualize quando houver obra entregue. |
| `modelo_valores_informados.csv` | Modelo do arquivo de lançamento manual dos indicadores. |
| `mapeamento_natureza_pls.csv` | Natureza de despesa → tema e subtema. Vale o **prefixo mais longo**: `33903943` (energia) é específico, e `339014` cobre todos os subitens de diárias. |
| `regras_texto_pls.csv` | Regex sobre a descrição do item de empenho: papel A4, copo descartável, toner, LED, fotovoltaica, resíduos, item sustentável. |
| `fatores_emissao.csv` | kg CO2e por passageiro-km, por faixa de distância (aéreo). |
| `elementos_despesa.csv` | Nome → código de categoria, grupo, modalidade e elemento. A API do Portal devolve só o nome. |

Para mudar a classificação: edite o CSV e rode `python run.py referencias` e
`indicadores`. O tema de cada despesa é recalculado pela natureza com a tabela
vigente, sem reprocessar `despesas`. Regras de texto (itens de empenho) exigem
reprocessar `despesas --offline`.

## Consumo físico: módulo `faturas`

O Portal não traz kWh nem m³, mas cada pagamento de energia (33903943) e água
(33903944) traz o **número do processo** e, na observação, o campus e a fatura. O
processo é público no SIPAC da UFPB (consulta pública, sem login nem CAPTCHA) e tem
a fatura em PDF com texto:

- **Energisa**: página 1 = resumo por unidade consumidora (kWh faturado, demanda,
  valores). As DANF3E das páginas seguintes dão o kWh **medido**, que o painel usa
  (difere do faturado só em UC cobrada pelo mínimo ou pela média).
- **CAGEPA**: "fatura agrupada", uma linha por ligação com leituras e m³ medido e
  faturado. O valor bruto bate com o pago no Portal.
- **Combustível** (33903001): relatório de abastecimentos da gerenciadora de frota,
  um registro por abastecimento (litros, R$, placa, posto, subunidade → campus), sem
  condutor/matrícula/cartão (LGPD). Layouts lidos: extrato da GOLDI (até mai/2024,
  conferido ao centavo com o total das faturas), "Abastecimentos" da PRIME
  (set/2024 em diante), "Relatório de Abastecimento/Faturamento" (out-nov/2025) e
  "Conferência NFe ANP" (dez/2025). **Lacuna**: jun-ago/2024 (PRIME) só tem tickets
  em R$, sem litros -- pedir o relatório à SULT/gerenciadora.
- **Resíduos de saúde** (33903978, só pagamentos à B-Green/Stericycle): relatório de
  fiscalização mensal da GMA/SINFRA, kg e R$ por campus → métrica `residuos_kg`.

Número do processo: o Portal grava em vários formatos (`004049/2024-54`,
`23074.017294/2026-72`, com ponto no fim e, desde 2026, só dígitos); todos são
normalizados (o DV tem 2 dígitos: `042864/2024-3752` é o `042864/2024-37`); campo vazio usa o número citado na observação, e erros de digitação conferidos no SIPAC ficam em `ref/processos_corrigidos.csv`.
Número com DV inválido (NUP: DV = 98 − (radical+número+ano × 100) mod 97) é procurado na base aberta de processos da UFPB (dadosabertos.ufpb.br, conjunto `processos-da-ufpb`, cache mensal em `data/raw/dadosabertos/processos_ufpb.parquet`, `faturas/processos_ufpb.py`): o único processo do mesmo ano, com o DV digitado, o assunto do tipo (unidade, interessado e assunto detalhado) e até 2 dígitos de diferença substitui o número; sem candidato único, os candidatos vão para a saúde (`faturas_processos`), e as trocas automáticas aparecem em `faturas_numeros`. Nos 454 processos de 2022–2026 recuperou os 4 erros conferidos à mão, sem falso positivo. Se o DV não bate, a busca no SIPAC repete com DV `99` (o SIPAC aceita e busca só por número e ano). Desde 2026 a observação não traz o campus: vale o assunto do processo
no SIPAC ("PAGAMENTO FATURA DA CAGEPA CAMPUS IV - MÊS 03/2026").

O mês do consumo é o de **referência da fatura**, não o do pagamento. Cada processo
consultado fica em `data/raw/sipac/<ano>/<processo>.json`; o PDF é apagado depois de
lido (`SIPAC_GUARDAR_PDF=1` para manter). Uma requisição a cada `SIPAC_PAUSA_S` (2 s)
ao servidor da universidade. Processo sem fatura legível fica registrado com o
motivo; `--refazer` tenta de novo.

## Capacitação na Escola Virtual de Governo: módulo `evg`

A ENAP publica no dados.gov.br um CSV por bimestre com todas as matrículas da EVG
(cerca de 600 mil por bimestre). O módulo lê cada arquivo em streaming e guarda só as
matrículas cuja **instituição declarada** é “Universidade Federal da Paraíba”.

- **O vínculo é declarado pelo aluno** (experiência profissional mais recente). Não
  confirma que a pessoa é servidor, e quem não preenche fica de fora. É um indicador
  **aproximado**. O dado exato está no SIGRH/PROGEP.
- **LGPD:** até 2024 os arquivos trazem nome e CPF parcial, que são descartados na leitura.
  Fica só `pessoa`, um hash com sal local (`EVG_SAL` ou `data/raw/evg/_sal.txt`), usado
  para contar pessoas distintas no ano.
- **Métricas:** `evg_matriculas`, `evg_certificados` (concluídas), `evg_horas_certificadas`
  e `evg_pessoas_sust`. Esta última conta cada pessoa no mês da primeira certificação em
  sustentabilidade do ano; a regra de sustentabilidade está em `ref/evg_sustentabilidade.csv`.
- **Indicadores:** A6-EVG-CERT (certificações, todos os cursos) e E6-CAPAC-01 (aproximado:
  pessoas certificadas em sustentabilidade ÷ docentes + técnicos da contagem da UFPB).
- **Arquivo novo da ENAP:** a cada bimestre, acrescente o id do Drive em
  `ref/evg_recursos.csv`. O dados.gov.br só lista os recursos com login.

## Editais e compras compartilhadas: módulo `compras` (fase 2)

Alimenta o N10 (contratações com critério de sustentabilidade), o N11 (compras
compartilhadas) e cinco indicadores do PLS que eram “integração”: E4-MARGEM-01,
E5-MULHERES-01, E5-MAOLOCAL-01, E5-AGRIC-01 e E4-BIM-01.

- **Lista das contratações:** o Compras.gov.br (`modulo-contratacoes`) lista pelo CNPJ da UFPB
  e pela modalidade (códigos do Compras: 05 pregão, 06 dispensa, 07 inexigibilidade, 03
  concorrência).
- **Documentos:** para licitações e dispensas, o painel baixa do PNCP o edital, o TR, o ETP e
  o aviso de contratação direta, e extrai o texto de cada página.
  - O texto fica em `data/raw/compras/docs/` (gzip). A classificação roda de novo a cada carga
    sobre esse cache, então mudar as regras não exige baixar nada.
  - Inexigibilidades (cerca de 350 por ano: assinaturas, cursos, credenciamentos) não têm os
    documentos lidos.
- **Regras** (`ref/criterios_editais.csv`), aplicadas ao texto sem acento e em maiúsculas:
  - **Critério específico** (logística reversa, destinação adequada, Procel, madeira legal,
    reciclado, gás refrigerante, cota social…): só conta fora do ETP, porque quem obriga é o
    TR ou o edital. As páginas são identificadas pelo cabeçalho do Compras.gov.br.
  - **Menção genérica** (IN 01/2010, Guia da AGU, PNRS): conta em qualquer página. Não entra
    no N10, porque o modelo de TR da AGU já traz a seção “Sustentabilidade” com esse texto.
  - **Universo** (dedicação exclusiva de mão de obra, alimentos, obra): vem do objeto da
    contratação. Os critérios desses indicadores (cota para mulheres, mão de obra local,
    agricultura familiar, BIM) vêm do texto.
- **Margem de preferência:** vem dos itens da licitação no PNCP.
- **Compras compartilhadas:** contam quatro situações:
  - atas das UASGs da UFPB com unidade participante de outro órgão;
  - atas da UFPB com adesão de outro órgão (`modulo-arp`);
  - contratos e empenhos da UFPB no PNCP cuja compra de origem é de outro órgão (participação);
  - os mesmos contratos quando têm o indicador de adesão (carona).
- **Limite do PNCP:** o servidor responde 429 com poucas dezenas de chamadas seguidas. O
  cliente faz 20 chamadas por minuto e espera 60 s quando recebe 429. A primeira carga leva
  algumas horas; as seguintes só leem compras novas ou atualizadas.

## Fornecedores locais e de pequeno porte: módulo `cnpj`

Alimenta o N12 (negócios de impacto nas contratações).

- **Pagamentos:** pago + RP pago a CNPJ, em aplicação direta (90) e nos elementos de
  contratação 30, 32, 33, 35, 37, 39, 40, 51 e 52, lidos de todo o cache diário do Portal
  (inclusive naturezas que o módulo `despesas` descarta).
- **Cadastro:** repositório de dados abertos da Receita (Nextcloud do SERPRO, pasta
  `Dados/Cadastros/CNPJ/AAAA-MM`, acesso público por WebDAV). Empresas, Estabelecimentos e
  Simples somam ~7 GB. Cada zip é baixado com retomada, filtrado pelos CNPJ pagos e apagado.
  O resultado fica em `data/raw/cnpj/`. Sem fornecedor novo, não baixa de novo.
- **Categorias (subtema de `pago_fornecedores`):** ME/EPP ou demais portes × sede na Paraíba
  ou em outros estados, mais “Agricultura familiar” (empenho com amparo da Lei 12.512/2011,
  11.947/2009 ou 14.628/2023), “Sem cadastro na Receita” e “Instituição financeira”.
- **Banco como favorecido** (CNAE 64) em natureza de contratação é depósito em conta
  vinculada de terceirizada ou arrecadação de fatura. O beneficiário real é outro, então
  fica fora da razão.
- **Limites:** o porte é o do cadastro na data da extração, não o da data do pagamento, e
  a UF é a do estabelecimento que recebeu.

## Fator de emissão do SIN: módulo `fator_sin`

```bash
python run.py fator_sin
```

Lê a página de fatores de emissão do SIRENE/MCTI, acha o link da planilha “Inventários Corporativos” (o nome muda a
cada atualização, ex. `Inventario_2026_janago.xlsx`), guarda em `data/raw/mcti/` e grava `pls_fator_sin` com o fator
médio mensal (tCO₂/MWh) de 2006 ao último mês publicado e o fator anual dos anos fechados. O escopo 2 do N03 usa
kWh do mês × fator do mês (como a ferramenta do GHG Protocol); mês ainda não publicado usa o anual do último ano
fechado e fica provisório (`saude`: info até 3 meses, atenção a partir de 4). Sem a planilha, vale o anual de
`ref/fatores_gee.csv`. Roda na carga mensal, antes de `indicadores`. O gov.br derruba requisição em conexão
reaproveitada: cada GET abre conexão nova.

## Índice sintético de execução do PLS: módulo `execucao`

É a medida geral de acompanhamento do plano, calculada sobre os **15 indicadores do núcleo**
(`ref/nucleo_pls.csv`). O painel web a mostra em `/pls/nucleo`.

- **Alcance de cada meta** (`alcance_pct` em `pls_metas`, de 0 a 100) — quanto da meta foi
  cumprido no ano:
  - mínimo: valor ÷ meta;
  - máximo: meta ÷ valor;
  - redução ou aumento: variação obtida ÷ variação prevista;
  - booleano: 0 ou 100.

  Piora conta 0 e meta superada conta 100. Ano parcial, linha de base e anos antes do plano
  não têm alcance.
- **Faixas** (`ref/faixas_execucao.csv`):
  - atingida (100);
  - próxima (75 ou mais);
  - em progresso (50 ou mais);
  - distante (menos de 50);
  - além das que não têm alcance: não avaliável, sem dado e sem meta.
- **Índice sintético** = `peso_metas` × alcance das metas + `peso_acoes` × cumprimento do plano
  de ações (N15), com pesos em `ref/indice_execucao.csv` (hoje 50/50).
  - O alcance das metas é a média por eixo e depois a média dos eixos, para cada eixo pesar
    igual.
  - No ano em curso, o índice usa o alcance do último ano fechado (`ano_metas`) e as ações do
    semestre.
  - Faltando um componente, o outro vale sozinho, e `componentes` diz qual entrou.
- **Cobertura:** indicadores avaliados sobre indicadores com meta, mostrada ao lado do índice.
- **Série e polaridade do núcleo:** além dos anos do índice, o nível `historico` grava o
  valor anual de cada Nxx desde o 1º ano com dado (com `ano_completo`), e cada indicador leva
  `polaridade` (`menor`, `maior` ou `neutro`), lida do texto de `ref/fichas_nucleo.csv`. A página
  inicial do painel usa as duas para mostrar a evolução e colorir a variação.
- **Metas:** ficam no catálogo (`ref/indicadores_pls.csv`: `tipo_meta`, `meta_valor`,
  `ano_base`) do indicador para onde cada Nxx aponta. Os tipos são `reducao_vs_base`,
  `reducao_anual`, `aumento_vs_base`, `aumento_anual`, `minimo`, `maximo`, `booleano` e
  `acompanhamento`. A sugestão de tipo para cada Nxx está em `meta_sugerida`, no núcleo.
- `conjunto=plano` calcula o mesmo índice sobre os 34 indicadores do PLS atual, para comparar.

## Saúde da carga: módulo `saude`

Roda no fim do `mensal`. Na carga mensal, um módulo que falha não derruba os seguintes:
a falha é registrada, os derivados usam o parquet anterior e o processo sai com código 1.

A verificação confere o que costuma pedir alguém:
- despesas atrasadas ou dias recusados pela CGU;
- processos sem fatura legível ou não achados no SIPAC;
- meses sem consumo lido;
- bimestre da EVG sem id cadastrado;
- fator do SIN provisório;
- censo do INEP novo;
- IPCA atrasado;
- fornecedores sem cadastro;
- ações vencidas ou sem acompanhamento;
- indicadores informados sem valor.

Cada item tem nível (erro, atenção, info ou ok), a lista concreta e o que fazer. O painel mostra
tudo em `/pls/saude`.

**Alerta por e-mail:** com `SMTP_HOST` e `ALERTA_EMAILS` no `.env`, o resumo de erros e pontos
de atenção vai por e-mail. Sem essas variáveis, a verificação só imprime e grava.

## Formulários dos setores: módulo `formularios`

Os setores preenchem no painel (`/pls/formularios`) o acompanhamento semestral das ações e os
valores dos indicadores informados. Assim ninguém precisa editar CSV.

- **Acesso:** um token por setor, criado pela TI. Só o hash SHA-256 fica no banco. O token
  libera as ações e os indicadores cujo `responsavel` casa com a expressão do acesso (`*` libera
  tudo, para a Comissão).
  ```
  python -m formularios.formularios criar "SINFRA" --responsavel "SINFRA"
  python -m formularios.formularios listar
  python -m formularios.formularios revogar "SINFRA"
  ```
- **Gravação:** a API só insere (`pls_form_acompanhamento`, `pls_form_valores`), e o usuário do
  Mongo dela não tem permissão para alterar nem apagar. O histórico de envios é a trilha de
  auditoria.
- **Regras validadas na API:**
  - situação compatível com o tipo da ação;
  - evidência obrigatória para concluída ou realizada;
  - justificativa obrigatória para suspensa, cancelada ou não realizada;
  - ano entre 2023 e o atual.
- **Do envio ao painel:** `run.py diario` (timer às 6h) leva o envio mais recente de cada chave
  para `data/metas/acompanhamento_acoes.csv` e `valores_informados.csv` e recalcula metas e ações.
  O CSV continua valendo para lançamento direto: um envio só o substitui para a mesma chave.

## Plano de ações do PLS: módulo `acoes`

**O plano** (`ref/acoes_pls_ufpb.csv`) tem 70 ações:
- as 61 ações das Tabelas 16 a 24 do PLS UFPB 2025–2029, cada uma com objetivo, meta, indicador do catálogo, responsável, prazos, recursos e riscos, conforme o PLS;
- 9 rotinas de governança da seção 7 do PLS e das Portarias SEGES 8.678/2021 e 5.376/2023 (comissão, publicação, reuniões mensais, relatórios semestral e anual, evento anual, plataforma de monitoramento, coleta de dados, revisão anual).

O plano muda só com revisão do PLS.

**O acompanhamento** (`data/metas/acompanhamento_acoes.csv`, modelo em `ref/modelo_acompanhamento_acoes.csv`) é preenchido pelos responsáveis a cada semestre (ciclo `AAAA-S1`/`AAAA-S2`, como os relatórios semestrais do PLS). Cada linha tem:
- `situacao`: `nao_iniciada`, `em_andamento`, `concluida`, `realizada_no_ciclo` (ações contínuas), `nao_realizada_no_ciclo`, `suspensa` ou `cancelada`;
- `percentual` de execução;
- `evidencia`: link ou processo SIPAC, obrigatória para concluída ou realizada;
- `justificativa` quando houver atraso;
- as quatro perguntas da avaliação da seção 7.2: avaliação, `facilitadores`, `dificuldades` e `ajuste_sugerido`.

Se o arquivo não existe, `python run.py acoes` cria uma linha em branco por ação para o ciclo atual. Para um ciclo novo, acrescente as linhas; vale a informação mais recente de cada ação.

**Situação calculada contra o prazo:**
- **entrega:** `concluida`, `em_andamento`, `atrasada` (prazo vencido e informada como não concluída), `vencida_sem_informacao`, `a_iniciar`, `sem_informacao`;
- **contínua:** `em_dia`, `pendente`, `sem_informacao`.

Ações com `verificacao=painel` (monitorar água, energia, combustível e resíduos, e a própria plataforma) ficam em dia quando o painel tem dado dos últimos 6 meses. As de `indicio` mostram o dado relacionado (itens de LED, cursos na EVG), mas a Comissão confirma.

**N15 do núcleo** (`ref/nucleo_pls.csv`): % das ações já iniciadas que estão concluídas, em dia ou em andamento no prazo. Concluída sem evidência não conta.

## Metas do PLS: módulo `metas`

Cada indicador do catálogo (`ref/indicadores_pls.csv`) tem um nível de automação:

| `automacao` | Significado | Origem do valor |
|---|---|---|
| `automatico` | calculado pelo ETL com dados públicos | coluna `calculo` (`ind:metrica=..,tema=..,subtema=a\|b,campo=..` soma `pls_indicadores` por ano) |
| `integracao` | há fonte estruturada a integrar (`tipo_fonte`: pública, fornecedor ou sistema interno) | lançamento manual até a integração existir |
| `informado` | só existe em documento | lançamento manual pela comissão |

Lançamento: `data/metas/valores_informados.csv` (modelo em `ref/`), uma linha por
indicador e ano, valor em formato brasileiro. Para `calculo=per_capita` (água),
lance o total do ano e o ETL divide pela comunidade acadêmica (`common/comunidade.py`). Um valor
lançado para indicador automático prevalece sobre o calculado.

`situacao` de cada ano: `atingida`, `nao_atingida`, `em_andamento` (ano incompleto
ou sem referência), `linha_de_base` (o próprio ano base) ou `acompanhamento`
(ampliação sem meta). Ano automático incompleto nunca aparece como não atingido.

A API expõe tudo em `GET /pls/metas` (`?eixo=1..6`, `?plano=true`) e o frontend
em `/pls/metas`.

> **Revisar antes de publicar**
> - Linhas com `confianca=conferir` (subitens do elemento 40 e alguns do 37/39). Confira na tabela de natureza de despesa vigente. O ETL lista essas linhas a cada carga.
> - Fatores de emissão: vêm da ferramenta do Programa Brasileiro GHG Protocol **v2022.1.1** (Tabela 12, aviação civil, sem forçamento radiativo), a última publicada em link aberto. A versão atual é distribuída mediante formulário no site do FGVces. Ao obtê-la, confira a Tabela 12 e atualize `kg_co2e_por_pkm`, usando os fatores "convertidos" (já divididos por 1,08) e sem `;` no texto da fonte.
> - Ao fim de cada carga, `despesas` lista as naturezas relevantes que ficaram **sem tema**. São candidatas a entrar no mapeamento.

## Relatório Anual de Avaliação de Desempenho

```bash
python relatorios/gerar_relatorio_anual.py --ano 2025 --saida <pasta>
```

Gera a minuta do relatório anual do PLS (Decreto 7.746/2012, Portaria SEGES/MGI 5.376/2023) em Word
(`relatorio_pls_<ano>.docx`, para a Comissão editar e juntar ao SEI) e HTML (versão web), com o mesmo
conteúdo: apresentação, metodologia (alcance, faixas, índice), visão geral do exercício, resultados por eixo
com a série do núcleo e leitura automática de cada indicador, detalhe de N10/N11/N12, plano de ações,
posição parcial do ano corrente, achados e recomendações cruzados dos dados, e anexos (fichas do núcleo e
saúde da carga). O que depende da Comissão sai como bloco "A preencher" destacado. Roda sobre
`data/processed` (depois de `mensal`/`diario`); padrão de `--ano` é o último ano fechado.

Variação anual acima de 30% entre anos completos é apontada para conferência com o setor antes de publicar
(`LIMITE_VARIACAO`).

## Automação das metas do PLS

`python relatorios/gerar_relatorio_metas.py [--saida DIR]` gera `automacao_metas_pls.docx`
(paisagem) e `.html`: para cada uma das 34 metas do plano (tabelas 16 a 24), se já é
automática, como foi automatizada, a fórmula, se precisa de aprimoramento (com prioridade) e
como aprimorar, mais o último valor apurado. A avaliação fica em
`ref/metas_aprimoramento.csv` (`id;precisa_aprimorar;prioridade;como_aprimorar`); o script
falha se alguma meta do catálogo ficar sem avaliação. Anexo: os indicadores de
acompanhamento (ampliações). `blocos.docx_doc` aceita `meta["paisagem"]`.

## Fichas técnicas dos indicadores do núcleo

```bash
python relatorios/gerar_fichas_nucleo.py --saida <pasta>
```

Word e HTML com uma ficha por indicador do núcleo: quadro-resumo (o que mede, fórmula, leitura, meta, responsável,
regra no painel), variáveis com base e campos, bases de dados, construção passo a passo, regras e filtros, cálculo
ano a ano (numerador, denominador, resultado), conferências, limitações e melhorias propostas; no fim, síntese das
melhorias e bases usadas. Os textos de construção vêm das famílias de `relatorios/gerar_construcao.py`; os textos
próprios do núcleo ficam em `ref/fichas_nucleo.csv`, `ref/variaveis_nucleo.csv` e `ref/melhorias_nucleo.csv`
(editáveis pela Comissão). Os dois relatórios usam `relatorios/blocos.py` (modelo de blocos + desenho Word/HTML).

## Validação cruzada com o Tesouro Gerencial

Referência externa para os totais: uma exportação do Tesouro Gerencial salva em
`data/validacao/tesouro_gerencial_liquidado.csv`:

```
ano;natureza;liquidado;pago
2024;3.3.90.39.43;6.123.456,78;6.001.234,56
```

- `natureza` pode vir com ou sem pontos.
- `pago` = Despesas Pagas + Restos a Pagar Pagos.
- Pode exportar **todas** as naturezas da UFPB: só as que estão no mapeamento PLS entram na comparação.
- Também aceita o formato antigo `ano;natureza;valor` (valor = liquidado).

**Gerar o arquivo a partir do Tesouro Gerencial:** monte o relatório com as linhas
`Ano Lançamento | Natureza Despesa Detalhada | Mês Lançamento`, as métricas
`DESPESAS LIQUIDADAS | DESPESAS PAGAS | 06. Restos a Pagar Pagos (F)` e o filtro
`Órgão UGE = 26240` mais os anos. Exporte em CSV e rode:

```bash
python validacao/converter_tesouro_gerencial.py "<exportação>.csv"
```

O mês nas linhas é obrigatório. As métricas do TG são saldos acumulados no ano: sem o
mês, o TG soma os saldos de todos os meses e os valores saem cerca de 6,5 vezes maiores.
O conversor usa o último período de cada ano (014, o encerramento, nos anos fechados).
A coluna de restos a pagar vem com soma corrida sobre um saldo que já é acumulado, e o
conversor desfaz isso usando a diferença entre os dois últimos períodos.

Com o arquivo presente, `despesas` imprime o comparativo `ano|natureza` de liquidado
e de pago e aponta divergências acima de 0,5%. As causas mais comuns são UG faltando
em `UGS` e dias do ano ainda não carregados.

## Decisões não óbvias

- **Histórico pelos arquivos, API só no fim da fila.** Os arquivos diários trazem a natureza completa (8 dígitos) por empenho impactado e a quantidade e o valor unitário de cada item. Pela API seria preciso converter nome em código, a quantidade não vem e há limite de requisições.
- **Consumo = pago (com restos a pagar), não liquidado nem empenhado.** Energia e água têm empenho estimativo anual em janeiro. E nos dados do Portal a **liquidação de restos a pagar vem com valor liquidado = 0**: em janeiro de 2025, 306 de 310 liquidações da UFPB eram de RP. O valor só aparece no pagamento (`valor pago + restos a pagar pagos`). O "liquidado" fica como métrica secundária, a do exercício corrente.
- **Só naturezas relevantes no fato.** Folha (3190.xx) e demais elementos fora do mapeamento não entram em `pls_despesas`.
- **Natureza do empenho, não da OB** (caminho da API). Uma ordem bancária pode pagar empenhos de elementos diferentes, por isso a natureza vem da NE impactada. Nos arquivos diários ela já vem por empenho impactado.
- **Viagens pelo CSV, não pela API.** O endpoint `/viagens` não traz trechos, e sem trecho não há distância nem emissão. O zip anual é lido por HTTP Range (`common/remote_zip.py`).
- **INEP por HTTP Range.** Do zip de ~450 MB, só o arquivo de IES (1 MB) e o de cursos (streaming) são lidos. `comunidade = matrículas de graduação + docentes em exercício + técnicos` é um **piso**: pós-graduação (CAPES) e terceirizados ficam de fora. Por isso o INEP só entra nos anos que a contagem da UFPB (`ref/comunidade_ufpb.csv`, com pós-graduação e terceirizados) não cobre; ano sem contagem usa o último disponível (`ano_comunidade`).
- **Quantidade de copos, papel A4 e toner.** O item de empenho do Portal vem com quantidade e valor unitário zerados; `compras/quantidades.py` (`python run.py quantidades`, na carga mensal depois de `compras`) divide o valor de cada item pelo preço homologado do mesmo item (número em "Item compra: NNNNN") nas compras por registro de preços da UFPB no PNCP e converte a unidade de fornecimento em copos, resmas de 500 folhas ou cartuchos. Sem compra no PNCP, vale a quantidade escrita no item ou o múltiplo comum dos valores do item no ano (embalagem presumida). Unidade do PNCP incompatível com o preço vai para `ref/itens_unidade_correcao.csv`; a saúde da carga lista o que ficou sem quantidade ou presumido. Resultado em `pls_itens_quantidade` e na métrica `quantidade_itens` (E1-COPOS-01 em copos, A1-PAPEL-QTD em resmas, A1-TONER-QTD em cartuchos). Mede **aquisição** (mês do empenho ou do pedido), não consumo (saídas do almoxarifado no SIPAC).
- **Almoxarifado Virtual Nacional (AVN).** O AVN é empenhado como serviço (3.3.90.39-84): o Portal só traz o valor. `compras/avn.py` (`python run.py avn`, antes de `quantidades`) pega os processos de pagamento ao operador (CNPJs em `ref/avn_operadores.csv`, citados nos pagamentos ou achados na base aberta de processos), baixa os ATESTADOS no SIPAC e lê o pedido do BRS Supply Manager anexado: produto, categoria, código, NCM, quantidade, preço, setor de entrega e mês do pedido (`pls_avn_itens`). Solicitante, aprovador, recebedor, e-mail e telefone são descartados na leitura (LGPD). Copos, papel e toner dos pedidos entram em `quantidade_itens` (método `avn`), e os pagamentos ao operador passam de não classificado para material de consumo, subtema "Almoxarifado Virtual Nacional (AVN)".
- **Meta projetada do ano corrente (proposta).** `execucao/projecao.py` calcula, para os 15 do núcleo, a meta do ano pelas regras de `ref/metas_2026_projecao.csv` (redução anual, redução sobre a base, mínimo, manter, faixa) e a projeção do ano: fluxos pelo mesmo período do ano anterior (jan até o último mês com dado), percentuais pelo acumulado. Sai no nível `projecao` de `pls_execucao`; as metas ainda serão validadas pela Comissão.
- **LGPD.** Favorecido pessoa física (diárias, ressarcimentos) fica sem CPF, nome e observação. Viagens ficam sem CPF, nome, cargo e motivo. O painel agrega, não identifica pessoas.
- **Certificados gov.br.** `download.inep.gov.br` não envia a cadeia intermediária. O `truststore` usa o repositório do sistema, que completa a cadeia.
- **Deflação no ETL.** `valor_real` está a preços do último mês com IPCA (`ref_ipca`). Todos os valores de `pls_indicadores` são aditivos entre subtemas, então a API só soma.

## Deploy (VM A, modo automático)

- `deploy/etl-pls-mensal.{service,timer}`: dia 10, 01h. De madrugada o limite da API é maior.
- `deploy/etl-pls-verificacao.{service,timer}`: dry-run no dia 9. As divergências ficam no journald e o cache já fica aquecido para o dia 10.
- `deploy/etl-pls-diario.{service,timer}`: todo dia às 6h, `run.py diario` (formulários → metas e ações).
- `deploy/init_mongo_users.js`: usuários `etl_user` (readWrite) e `api_user` (read + papel `formulariosInsert`, que só insere nas coleções dos formulários), mais os índices. Em banco já criado, rode só o `createRole` e o `grantRolesToUser` indicados no script.
- `.env` do ETL: `SMTP_*`, `ALERTA_EMAILS` e `PAINEL_URL` para o alerta da saúde da carga.
