# pls_ufpb-backend

API somente leitura do Painel PLS (FastAPI + Motor). Ouve só em `127.0.0.1:8001`.
O único cliente é o Next.js (BFF). Lê a coleção `pls_indicadores`, gerada pelo
módulo `indicadores` do ETL, e `pls_temas` para os rótulos.

| Rota | Conteúdo |
|---|---|
| `GET /pls/paineis` | Painéis declarados em `app/panels.py` |
| `GET /pls/filtros` | Anos, temas (rótulo e eixo, na ordem de `ref/temas_pls.csv`) e métricas |
| `GET /pls/{slug}` | Séries e cards de destaque. Parâmetros: `granularidade=ano\|mes`, `valor=real\|nominal\|per_capita`, `ano_inicio`, `ano_fim`, `por=tema_codigo\|subtema` |
| `GET /pls/execucao` | Índice sintético, eixos e indicadores (`?conjunto=nucleo\|plano`). No núcleo, cada indicador traz `polaridade` e `historico` (série anual desde o 1º ano com dado) |
| `GET /health` | ok |

Os cards comparam o **último ano completo** com o anterior. O ano corrente incompleto
daria uma queda falsa.

**Novo painel:** acrescente um `PanelDef` em `app/panels.py`, com temas, métricas e
rótulos. A rota é registrada sozinha por `app/panel_routes.py`.

```bash
pip install -r requirements-dev.txt
copy .env.example .env
uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
python -m pytest        # Mongo em memoria (mongomock-motor), inclui teste do rate limit
```

Segurança (padrão da equipe): somente GET, CORS restrito a `FRONTEND_ORIGIN`,
`/docs` desligado em `APP_ENV=production`, modelos Pydantic explícitos em
`app/models/pls.py` e `slowapi` a 60 req/min.

O limite do `slowapi` só vale com o `SlowAPIMiddleware` registrado, como está em
`app/main.py`. `default_limits` sozinho não limita nada, e o teste
`test_rate_limit_60_por_minuto` cobre isso.
