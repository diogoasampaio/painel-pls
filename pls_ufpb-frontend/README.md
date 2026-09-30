# pls_ufpb-frontend

Next.js 15 (App Router) + React 19 + Recharts, em modo servidor (`next start`),
atuando como BFF. `basePath` é `/painel-pls`. A API interna é chamada só
server-side, via `API_BASE_URL`, nunca com prefixo `NEXT_PUBLIC_`.

| Rota | Conteúdo |
|---|---|
| `/painel-pls/pls` | **Visão geral** (aba 1): hero, índice sintético, execução do ano frente à meta projetada, os 15 números do núcleo, leitura executiva automática e "O que é o PLS" |
| `/painel-pls/pls/eixos?eixo=1` | **Eixos do PLS** (aba 2): indicadores do eixo com evolução anual, projeção do ano corrente e meta projetada (proposta a validar) |
| `/painel-pls/pls/indicadores?i=N02` | **Indicadores** (aba 3): ficha, números, série anual, execução do ano e dados de origem do painel temático (consumo, gasto, combustível) |
| `/painel-pls/pls/metas`, `/nucleo`, `/saude` | Catálogo de metas, índice e faixas, saúde da carga |
| `/painel-pls/pls/indicadores-globais` | Visão geral: todos os temas, quebrados por tema |
| `/painel-pls/pls/[slug]` | Painel temático: energia, água, material de consumo, contratações, deslocamento |

As três abas ficam em `components/Abas.tsx`, abaixo do cabeçalho. A meta projetada
e a projeção do ano vêm do ETL (`execucao/projecao.py`, regras em
`ref/metas_2026_projecao.csv`) pelo campo `projecao` de `/pls/execucao`.

Os controles (R$ constantes / correntes / per capita; anual / mensal) mudam a
query string. O estado fica na URL. Componentes do DS com hooks (cards, gráfico, seletores) rodam no cliente.

**Aviso de validação:** enquanto a Comissão do PLS confere os dados, todas as páginas mostram no topo a faixa
"Versão em validação" (`components/AvisoValidacao.tsx`). Ela sai com `PAINEL_EM_VALIDACAO=nao` no `.env` do servidor
(padrão: ligada), sem mudar código.

## Design system: LEMA-DS

Componentes do [LEMA-DS](https://ds.lema.ufpb.br) (registry shadcn da UFPB), com
Tailwind CSS v4. `components.json` declara o registry `@lema-ds`:

```bash
npx shadcn@latest add @lema-ds/<item> --yes     # ex.: @lema-ds/ds-bullet-chart
```

- O código instalado cai em `components/ui/` e `lib/` e **não se edita**. Para
  atualizar, rode o `add` de novo (ele sobrescreve o arquivo).
- Tokens em `app/globals.css`: base neutra do DS, temas `.blue`, `.green` e
  `.violet` e semânticos (`success`, `warning`, `risk-1..4`).
- **Identidade:** tema `ufpb` (padrão) com as cores do brasão; cabeçalho com
  o brasão e o logo do PLS e rodapé com a PROPLAN como desenvolvedora
  (`components/Marcas.tsx`). Arquivos em `public/marcas/`: `ufpb-brasao.png`
  (original) e `ufpb-brasao-168.png` (cópia leve usada no cabeçalho),
  `pls-ufpb.png` e `proplan.png`.
- **Página inicial** (`app/pls/page.tsx`, `components/Hero.tsx`): a composição de
  dashboard da hero é ilustrativa (sem valores, com legenda dizendo isso); os
  números reais vêm logo abaixo (índice de execução, contagem de indicadores por
  eixo). O rótulo em caixa alta acima do título foi pedido pela UFPB, apesar da
  "No-Eyebrow Rule" do DS.
- `next.config.ts` tem `optimizePackageImports: ["radix-ui"]`: sem isso, importar
  o botão do DS (que usa o `Slot` do pacote-barril `radix-ui`) levava todos os
  primitivos Radix ao navegador (página inicial: 223 kB → 108 kB).
- **Tema por projeto:** `TEMA_DS` no `.env` (`neutro`, `blue`, `green` ou
  `violet`; padrão `blue`, `lib/tema.ts`) põe a classe no `<html>`. O tema troca
  `primary`, `secondary`, `accent` e `ring`; cores semânticas e de gráfico não
  mudam. Páginas estáticas leem a variável no build, então defina antes do `next build`. Rawline segue como a única
  família tipográfica (padrão gov.br).
- `.polaridade-menor-melhor`: o `ds-card-stat` pinta a queda de vermelho e não
  tem opção de polaridade. No PLS, cair é bom, então essa classe troca
  `success` e `destructive` no trecho em que é aplicada.
- Telas migradas: **Destaques** (`ds-card-stat`) e **Metas** (`card`, `ds-badge` para a situação e `ds-bullet-chart` para valor x meta: meta de mínimo compara o próprio valor; meta de redução compara a redução obtida com a pedida, só quando há queda; sem meta numérica, fica só o texto). **Saúde** (`Kpi` = `ds-card-stat` com ícone, `ds-badge` por nível, `table`) e **Núcleo** (`card`, `ds-badge` e barra de faixas com as cores de `lib/faixas.ts`: success e risk-1..4, já que o DS não tem barra empilhada de contagens). **Seletores** (valor, período, eixo e abas do formulário): `ds-pill-group`. O pill-group é de botões, então `components/Seletor.tsx` faz cada escolha virar `router.push` para a URL da opção. O estado continua na query string, e no celular as opções rolam na horizontal em vez de quebrar. **Gráfico** (`SerieChart`): `ds-bar-chart` empilhado, com legenda clicável. Cores só por token: `--chart-1..5` do DS mais `--chart-6..10` do painel (até 10 séries). O tema `.blue` não sobrescreve as cores de gráfico, porque séries por categoria em tons de uma cor só ficariam indistinguíveis. As demais usam o CSS legado,
  no fim do `globals.css`, que já lê os mesmos tokens. A camada base devolve
  margens e listas que o preflight do Tailwind zera, só fora dos componentes do
  DS (`[data-slot]`).

```bash
npm install
copy .env.example .env.local
npm run dev        # http://localhost:3000/painel-pls
```

Deploy: `deploy/painel-pls-web.service` (porta 3001) e `deploy/nginx-location.conf`,
um bloco `location /painel-pls` a acrescentar no server já existente do Nginx.
