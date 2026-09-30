# Implantação nas máquinas virtuais

Painel de Sustentabilidade (PLS) da UFPB na mesma infraestrutura do `prpg_avaliacao`:

```
                 ┌──────────────────────────── VM A (aplicação) ─────────────────────────────┐
Navegador ─HTTPS─> Nginx :443 ── /painel-pls ──> Next.js :3001 (painel-pls-web)              │
                 │                                   └─ server-side ─> FastAPI 127.0.0.1:8001 │
                 │                                                     (painel-pls-api)      │
                 │ ETL (systemd timers: diário 06h, verificação dia 9, carga mensal dia 10)  │
                 └─────────────────────────────────────┬─────────────────────────────────────┘
                                                       │ 27017 (só a partir da VM A)
                 ┌──────────────── VM B (banco) ───────┴──────┐
                 │ MongoDB, banco lógico painel_pls            │
                 │ etl_user (leitura e escrita), api_user (leitura + insert dos formulários) │
                 └─────────────────────────────────────────────┘
```

A API só ouve em `127.0.0.1` e nunca é publicada no Nginx. O único ponto público é o Next.js em `/painel-pls`.

---

## 1. Pré-requisitos

**VM A**

| Item | Versão ou valor |
|---|---|
| Python | 3.12 ou superior (desenvolvido em 3.13) |
| Node.js | 22 LTS |
| git | com chave de implantação (deploy key) do repositório |
| Nginx | o `server{}` que já atende `/prpg-avaliacao` |
| Recursos a mais | ~0,5 GB de RAM contínuo, pico de 1–1,5 GB na carga mensal (madrugada); ~10 GB de disco livre |

Saída HTTPS liberada para as fontes do ETL: `portaldatransparencia.gov.br`, `sipac.ufpb.br`,
`dadosabertos.ufpb.br`, `pncp.gov.br`, `dadosabertos.compras.gov.br`, `api.bcb.gov.br`,
`download.inep.gov.br`, `www.gov.br` (MCTI), `dados.gov.br` e `drive.google.com` (Escola Virtual
de Governo), `arquivos.receitafederal.gov.br` (cadastro de CNPJ).

**VM B**: MongoDB já em uso pelo `prpg_avaliacao`, com `security.authorization: enabled` e a porta
27017 aberta só para a VM A.

## 2. Banco (VM B, uma vez)

```bash
# troque as duas senhas no script antes de rodar
mongosh -u admin -p --authenticationDatabase admin painel_pls pls_ufpb-etl/deploy/init_mongo_users.js
```

Cria `etl_user` e `api_user` e os índices usados pela API.

## 3. Código (VM A)

Repositório privado `diogoasampaio/painel-pls` (se for transferido para a organização `codeinfo-ufpb`, troque
o endereço abaixo). Na VM, use uma **deploy key somente leitura**
(GitHub → Settings → Deploy keys), não a chave pessoal de ninguém.

```bash
sudo mkdir -p /opt/painel-pls && sudo chown codeinfo: /opt/painel-pls
sudo -u codeinfo git clone git@github.com:diogoasampaio/painel-pls.git /opt/painel-pls/src

# caminhos que os arquivos de serviço (deploy/*.service) esperam
sudo ln -s /opt/painel-pls/src/pls_ufpb-backend  /opt/painel-pls/backend
sudo ln -s /opt/painel-pls/src/pls_ufpb-frontend /opt/painel-pls/frontend
sudo ln -s /opt/painel-pls/src/pls_ufpb-etl      /opt/pls-etl

# usuário do ETL e a pasta de dados (fora do código: cache das fontes e parquets)
sudo useradd --system --home /var/lib/pls-etl --shell /usr/sbin/nologin pls-etl
sudo mkdir -p /var/lib/pls-etl && sudo chown pls-etl: /var/lib/pls-etl && sudo chmod 750 /var/lib/pls-etl
```

O ETL só escreve em `DATA_DIR`. O código fica com o dono `codeinfo`, e `pls-etl` só precisa ler.

## 4. Configuração (`.env` de cada parte)

Copie os exemplos e preencha. Os `.env` **nunca** vão para o git.

```bash
cd /opt/painel-pls/src
cp pls_ufpb-etl/.env.example      pls_ufpb-etl/.env
cp pls_ufpb-backend/.env.example  pls_ufpb-backend/.env
cp pls_ufpb-frontend/.env.example pls_ufpb-frontend/.env
sudo chown pls-etl: pls_ufpb-etl/.env && sudo chmod 600 pls_ufpb-etl/.env
chmod 600 pls_ufpb-backend/.env pls_ufpb-frontend/.env
```

| Arquivo | Variáveis que mudam na VM |
|---|---|
| `pls_ufpb-etl/.env` | `MONGO_URI=mongodb://etl_user:<senha>@<ip-vm-b>:27017/?authSource=painel_pls`, `DATA_DIR=/var/lib/pls-etl`, `PORTAL_API_KEY` (chave da API do Portal da Transparência), `SMTP_*` e `ALERTA_EMAILS` (e-mail da saúde da carga), `PAINEL_URL=https://<servidor>/painel-pls` |
| `pls_ufpb-backend/.env` | `APP_ENV=production`, `MONGO_URI=mongodb://api_user:<senha>@<ip-vm-b>:27017/?authSource=painel_pls`, `FRONTEND_ORIGIN=https://<servidor>` |
| `pls_ufpb-frontend/.env` | `API_BASE_URL=http://127.0.0.1:8001`, `TEMA_DS=ufpb`, `PAINEL_EM_VALIDACAO=sim` (faixa "Versão em validação"; `nao` quando a Comissão validar) |

## 5. Instalação

```bash
cd /opt/painel-pls/src
python3 -m venv pls_ufpb-etl/.venv     && pls_ufpb-etl/.venv/bin/pip install -r pls_ufpb-etl/requirements.txt
python3 -m venv pls_ufpb-backend/.venv && pls_ufpb-backend/.venv/bin/pip install -r pls_ufpb-backend/requirements.txt
cd pls_ufpb-frontend && npm ci && npm run build      # TEMA_DS é lido no build
```

## 6. Primeira carga (ETL)

Rode como `pls-etl`, na ordem abaixo. A carga completa é longa: os arquivos diários do Portal saem
a 4 por minuto desde 2023, e o SIPAC é consultado com pausa de 2 s. Rode de madrugada e acompanhe
com `journalctl` ou redirecionando a saída para um arquivo.

```bash
cd /opt/pls-etl
sudo -u pls-etl .venv/bin/python run.py referencias   # catálogo, mapeamentos e decisões da Comissão
sudo -u pls-etl .venv/bin/python run.py inep          # anual e manual (censo da educação superior)
sudo -u pls-etl .venv/bin/python run.py mensal        # todas as fontes + indicadores, metas, ações, execução e saúde
```

`mensal` roda, nesta ordem: referências, IPCA, fator do SIN, despesas, faturas, viagens, compras,
AVN, quantidades, CNPJ, EVG, indicadores, formulários, metas, ações, execução e saúde. Um módulo que
falha não derruba os seguintes, e a falha aparece na saúde da carga.

**Para encurtar a primeira carga**, copie o cache de fontes já baixado na máquina de
desenvolvimento (pasta `data/raw` do ETL) para `/var/lib/pls-etl/raw` pela rede interna
(`rsync`/`scp`). Esse cache fica só no servidor: **não** vai para o git nem para fora da UFPB.

## 7. Serviços (systemd e Nginx)

```bash
cd /opt/painel-pls/src
sudo cp pls_ufpb-backend/deploy/painel-pls-api.service  /etc/systemd/system/
sudo cp pls_ufpb-frontend/deploy/painel-pls-web.service /etc/systemd/system/
sudo cp pls_ufpb-etl/deploy/etl-pls-*.service pls_ufpb-etl/deploy/etl-pls-*.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now painel-pls-api painel-pls-web
sudo systemctl enable --now etl-pls-diario.timer etl-pls-verificacao.timer etl-pls-mensal.timer
```

| Unidade | O que faz |
|---|---|
| `painel-pls-api` | FastAPI em 127.0.0.1:8001 (usuário `codeinfo`) |
| `painel-pls-web` | Next.js em :3001 (usuário `codeinfo`) |
| `etl-pls-diario.timer` | 06h: formulários dos setores → metas, ações e execução |
| `etl-pls-verificacao.timer` | dia 9, 01h: `mensal --dry-run` (divergências no journald) |
| `etl-pls-mensal.timer` | dia 10, 01h: carga mensal completa, com e-mail da saúde da carga |

Sugestão para não afetar o `prpg_avaliacao` na carga mensal: acrescente em `etl-pls-mensal.service`,
na seção `[Service]`, `MemoryMax=2G` e `Nice=10`.

**Nginx:** acrescente o bloco de `pls_ufpb-frontend/deploy/nginx-location.conf` dentro do `server{}`
que já atende `/prpg-avaliacao`, depois `sudo nginx -t && sudo systemctl reload nginx`.

## 8. Acessos dos setores aos formulários

Cada setor recebe um token (só o hash fica no banco). O token é mostrado uma única vez:

```bash
cd /opt/pls-etl
# --responsavel: expressão casada com a coluna "responsável" das ações e indicadores ("*" = Comissão, tudo)
sudo -u pls-etl .venv/bin/python -m formularios.formularios criar SINFRA --responsavel "SINFRA"
sudo -u pls-etl .venv/bin/python -m formularios.formularios criar Comissao --responsavel "*"
sudo -u pls-etl .venv/bin/python -m formularios.formularios listar
sudo -u pls-etl .venv/bin/python -m formularios.formularios revogar SINFRA
```

Entregue o token ao setor por canal seguro (não por e-mail aberto a terceiros).

## 9. Conferência

```bash
curl -s http://127.0.0.1:8001/pls/paineis | head -c 300           # API
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:3001/painel-pls/pls
journalctl -u etl-pls-mensal --since today                        # log da carga
systemctl list-timers 'etl-pls-*'                                  # próximas execuções
```

No navegador: `https://<servidor>/painel-pls/pls`. A página **Saúde da carga**
(`/painel-pls/pls/saude`) mostra o que ficou pendente na última carga.

## 10. Atualizações

```bash
cd /opt/painel-pls/src && sudo -u codeinfo git pull
pls_ufpb-etl/.venv/bin/pip install -r pls_ufpb-etl/requirements.txt
pls_ufpb-backend/.venv/bin/pip install -r pls_ufpb-backend/requirements.txt
cd pls_ufpb-frontend && npm ci && npm run build && cd ..
sudo systemctl restart painel-pls-api painel-pls-web
# mudou algo em pls_ufpb-etl/ref/ (catálogo, decisões, regras)? recarregue as referências e os derivados:
cd /opt/pls-etl && sudo -u pls-etl .venv/bin/python run.py referencias && sudo -u pls-etl .venv/bin/python run.py diario
```

Tarefas manuais recorrentes:

| Quando | O quê |
|---|---|
| Uma vez por ano | Contagem da comunidade acadêmica: `python -m common.comunidade <planilha.xlsx>` (atualiza `ref/comunidade_ufpb.csv`, que vai pelo git) |
| Quando o censo sair (fim do ano seguinte) | `python run.py inep` |
| A cada bimestre da EVG | Acrescentar o id do arquivo em `ref/evg_recursos.csv` (a saúde da carga avisa) |
| Decisões da Comissão | Registrar em `ref/decisoes_comissao.csv` (situação `decidida` e a decisão) |
| Fim da validação | `PAINEL_EM_VALIDACAO=nao` no `.env` do frontend e `sudo systemctl restart painel-pls-web` |

## 11. Segurança e LGPD

- Repositório **privado**. Sem `.env`, sem `data/` e sem relatórios gerados (`.gitignore`).
- A API só ouve em 127.0.0.1. O MongoDB só aceita a VM A, com usuários de menor privilégio.
- O ETL descarta nome, CPF, matrícula e dados de contato na leitura (despesas de pessoa física,
  viagens, frota, pedidos do AVN). O cache de fontes em `/var/lib/pls-etl` fica restrito ao usuário `pls-etl`.
- Backup: o banco `painel_pls` entra na rotina de backup do MongoDB da VM B. O cache em
  `/var/lib/pls-etl/raw` é recuperável baixando de novo as fontes, mas economiza horas de carga.
