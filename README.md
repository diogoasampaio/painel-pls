# Painel de Sustentabilidade (PLS) da UFPB

Indicadores do Plano de Logística Sustentável a partir de dados públicos.
Segue o padrão de arquitetura da equipe (`prpg_avaliacao`): três camadas
isoladas, com o frontend como único ponto público.

```
Navegador ─HTTPS─> Nginx :443 ─> Next.js :3001 (BFF, basePath /painel-pls)
                                   └─fetch server-side─> FastAPI 127.0.0.1:8001 (só GET)
                                                           └─read-only─> MongoDB painel_pls (VM B)
ETL (systemd timer, mensal) ─readWrite─> MongoDB painel_pls
```

| Pasta | Papel |
|---|---|
| [pls_ufpb-etl](pls_ufpb-etl/README.md) | Extração (Portal da Transparência API + CSV, BCB, INEP), mapeamento PLS em `ref/`, agregados |
| [pls_ufpb-backend](pls_ufpb-backend/README.md) | FastAPI somente leitura; painéis declarados em `app/panels.py` |
| [pls_ufpb-frontend](pls_ufpb-frontend/README.md) | Next.js + Recharts |

## Módulo PLS: fatia vertical

```
ETL: referencias, despesas, viagens, ipca, inep  ->  indicadores (derivado)
Mongo: pls_despesas, pls_itens_empenho, pls_viagens, pls_trechos, ...  ->  pls_indicadores
API: /pls/paineis  /pls/filtros  /pls/{slug}
Web: /pls  /pls/indicadores-globais  /pls/[slug]
```

## Respostas às perguntas de início de projeto

1. **Módulos (fontes):** despesas (Portal API), viagens (Portal CSV), IPCA (BCB), comunidade acadêmica (INEP), mais as tabelas de mapeamento do PLS.
2. **Formato e LGPD:** APIs públicas e CSV. Há dado pessoal na fonte (CPF e nome de viajantes e de favorecidos PF), e ele é **descartado no ETL**.
3. **Acesso:** dados públicos, então o painel pode ser público.
4. **VM e banco:** a mesma VM A e o mesmo MongoDB do `prpg_avaliacao`, com banco lógico próprio (`painel_pls`), API na porta 8001 e web na 3001.
5. **basePath:** `/painel-pls`.
6. **Modo do ETL:** automático (timer mensal no dia 10). Só o INEP é manual (anual).

## Próximos módulos (fora do escopo atual)

- **Compras sustentáveis** (PCA/CATMAT, PNCP): reaproveitar os extratores de `../pls/pls_mvp_ufpb` como módulo `compras`.
- **Consumo físico** (kWh, m³): planilha mensal da Prefeitura Universitária como módulo manual `consumo_fisico`, no mesmo padrão do `prpg_avaliacao` (Excel + `EXPECTED_TOTALS`).
- **Emissões da frota:** os trechos já trazem "veículo oficial/próprio" com distância. Falta o fator por km.
- **Benchmark entre IFES:** `pls_comunidade` já traz as 69 universidades federais. Falta extrair despesas de outras UGs.
