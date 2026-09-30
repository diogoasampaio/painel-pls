import Link from "next/link";
import { DecisoesComissao } from "@/components/DecisoesComissao";
import { MetaProgresso } from "@/components/MetaProgresso";
import { Seletor } from "@/components/Seletor";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge, type BadgeProps } from "@/components/ui/ds-badge";
import { getMetas, type IndicadorMeta, type ValorMeta } from "@/lib/api";
import { formatValor } from "@/lib/format";

type Props = { searchParams: Promise<Record<string, string | undefined>> };

const AUTOMACAO: Record<IndicadorMeta["automacao"], string> = {
  automatico: "Automático",
  integracao: "Automatizável",
  informado: "Informado pela comissão",
};

const FONTE: Record<IndicadorMeta["tipo_fonte"], string> = {
  publica: "dados públicos",
  fornecedor: "dados do fornecedor",
  interna: "sistema interno da UFPB",
  documental: "registro documental",
};

const SITUACAO: Record<ValorMeta["situacao"], { texto: string; variante: BadgeProps["variant"] }> = {
  atingida: { texto: "Meta atingida", variante: "success" },
  nao_atingida: { texto: "Meta não atingida", variante: "destructive" },
  em_andamento: { texto: "Em andamento", variante: "secondary" },
  linha_de_base: { texto: "Linha de base", variante: "outline" },
  historico: { texto: "Histórico (antes da linha de base)", variante: "outline" },
  acompanhamento: { texto: "Acompanhamento", variante: "outline" },
};

/**
 * O que o bullet compara: meta de minimo -> o proprio valor; meta de reducao ->
 * a reducao ja obtida (-variacao) contra a reducao pedida. Sem meta numerica,
 * sem valor ou com aumento no lugar de reducao, nao ha barra (fica o texto).
 */
function progresso(ind: IndicadorMeta, v: ValorMeta) {
  if (ind.meta_valor == null || v.valor == null) return null;
  const rotulo = `${v.ano}${v.ano_completo ? "" : " parcial"}`;
  if (ind.tipo_meta === "minimo") return { rotulo, valor: v.valor, meta: ind.meta_valor, percentual: ind.unidade === "%" };
  if (ind.tipo_meta.startsWith("reducao") && v.variacao_pct != null && v.variacao_pct <= 0)
    return { rotulo: `Redução ${v.ano}`, valor: -v.variacao_pct, meta: ind.meta_valor, percentual: true };
  return null;
}

function UltimoValor({ ind }: { ind: IndicadorMeta }) {
  const v = ind.valores.at(-1);
  if (!v) return <p className="text-sm text-muted-foreground">Sem valor ainda</p>;
  const unidade = ind.unidade === "R$" ? "R$" : ind.unidade;
  const barra = progresso(ind, v);
  const situacao = SITUACAO[v.situacao];
  return (
    <div className="flex flex-col gap-2">
      <p className="flex flex-wrap items-center gap-x-2 gap-y-1 text-sm">
        <span>
          <span className="font-semibold tabular-nums">{formatValor(v.valor, unidade)}</span> em {v.ano}
          {!v.ano_completo && " (parcial)"}
        </span>
        {v.valor_nominal != null && v.ref_ipca && (
          <span className="text-muted-foreground">
            R$ de {v.ref_ipca.slice(5)}/{v.ref_ipca.slice(0, 4)}; nominal {formatValor(v.valor_nominal, unidade)}
          </span>
        )}
        {v.alcance_pct != null && <span>alcance {v.alcance_pct.toFixed(0)}% da meta</span>}
        {v.variacao_pct != null && (
          <span className="tabular-nums">
            {v.variacao_pct > 0 ? "+" : ""}
            {v.variacao_pct.toFixed(1).replace(".", ",")}% sobre {v.ano_referencia}
          </span>
        )}
        <Badge variant={situacao.variante}>{situacao.texto}</Badge>
      </p>
      {barra && <MetaProgresso {...barra} />}
    </div>
  );
}

/** Metas do PLS 2025-2029 por eixo: o plano inteiro, com ou sem valor. */
export default async function MetasPls({ searchParams }: Props) {
  const q = await searchParams;
  const eixo = q.eixo && /^[1-6]$/.test(q.eixo) ? q.eixo : undefined;
  const { eixos, indicadores } = await getMetas({ eixo });
  const contagem = (a: IndicadorMeta["automacao"]) => indicadores.filter((i) => i.id.startsWith("E") && i.automacao === a).length;

  return (
    <main className="container">
      <h1 className="page-title">Metas do PLS 2025–2029</h1>
      <p className="caption">
        Indicadores do plano (tabelas 16 a 24) e ampliações do painel. Do plano: {contagem("automatico")} automático(s),{" "}
        {contagem("integracao")} automatizáveis por integração e {contagem("informado")} informados pela comissão.
      </p>
      <p className="caption">
        O índice sintético de execução e as faixas ficam no <Link href="/pls/nucleo">Painel do PLS</Link>, calculados
        sobre os 15 indicadores do núcleo. Na barra, o traço vertical é a meta.
      </p>
      <nav className="mb-5 max-w-full" aria-label="Eixo">
        <Seletor
          rotulo="Eixo"
          atual={eixo ?? "todos"}
          opcoes={[
            { valor: "todos", texto: "Todos", href: "/pls/metas" },
            ...eixos.map((e) => ({ valor: e.eixo_pls, texto: `Eixo ${e.eixo_pls}`, href: `/pls/metas?eixo=${e.eixo_pls}` })),
          ]}
        />
      </nav>
      {eixos
        .filter((e) => !eixo || e.eixo_pls === eixo)
        .map((e) => {
          const lista = indicadores.filter((i) => i.eixo_pls === e.eixo_pls);
          if (!lista.length) return null;
          return (
            <section key={e.eixo_pls} className="mt-8 flex flex-col gap-4">
              <h2 className="section-title">
                Eixo {e.eixo_pls} · {e.eixo}
              </h2>
              {lista.map((i) => (
                <Card key={i.id} size="sm">
                  <CardHeader>
                    <CardDescription>
                      {i.id.startsWith("A") ? "Ampliação do painel" : `Tabela ${i.tabela_pls} · ${i.objetivo}`}
                    </CardDescription>
                    <CardTitle>{i.indicador}</CardTitle>
                    {/* abaixo do título, e não em CardAction: no canto, espreme o título no celular */}
                    <div>
                      <Badge variant="outline">
                        {AUTOMACAO[i.automacao]} · {FONTE[i.tipo_fonte]}
                      </Badge>
                    </div>
                  </CardHeader>
                  <CardContent className="flex flex-col gap-3">
                    <p className="text-sm">
                      <span className="text-muted-foreground">Meta:</span> {i.meta}
                    </p>
                    <UltimoValor ind={i} />
                    <DecisoesComissao decisoes={i.decisoes} />
                    <details className="text-sm text-muted-foreground">
                      <summary className="cursor-pointer">Fórmula e rota de automação</summary>
                      <div className="mt-2 flex flex-col gap-2">
                        <p>{i.formula}</p>
                        <p>
                          <span className="font-semibold">Rota:</span> {i.rota_automacao}{" "}
                          <span className="font-semibold">Responsável:</span> {i.responsavel}
                        </p>
                      </div>
                    </details>
                  </CardContent>
                </Card>
              ))}
            </section>
          );
        })}
    </main>
  );
}
