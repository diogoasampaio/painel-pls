import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { BarraAlcance, Dado } from "@/components/CartaoExecucao";
import { DecisoesComissao } from "@/components/DecisoesComissao";
import { EvolucaoChart } from "@/components/EvolucaoChart";
import { complementar, ICONE_INDICADOR, Medalhao, PilulasEixos, PilulasLink, SelosGrupo, SituacaoBadge, TOM_EIXO, textoMeta } from "@/components/Nucleo";
import { SerieChart } from "@/components/SerieChart";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { getExecucao, getPainel, type Painel, type PontoSerie } from "@/lib/api";
import { comoProjetou, completos, DADOS_ASSOCIADOS, SEM_PAINEL, fmt, nomeEixo, periodo, regraMeta, rotuloEixo, variacao, type Ind } from "@/lib/pls";

export const dynamic = "force-dynamic";

type Props = { searchParams: Promise<{ i?: string }> };

/** Painéis de gasto de apoio: alimentam os gráficos filtrados, mas não entram na navegação principal. */
const FORA_DA_NAVEGACAO = new Set(["contratacoes"]);

const SENTIDO: Record<string, string> = {
  menor: "Quanto menor, melhor",
  maior: "Quanto maior, melhor",
  neutro: "Depende do contexto (sem sentido desejado único)",
};

function Ficha({ i }: { i: Ind }) {
  const linhas: [string, string | null | undefined][] = [
    ["Fórmula", i.formula],
    ["Meta no PLS", i.meta || i.meta_sugerida],
    ["Sentido desejado", SENTIDO[i.polaridade ?? "neutro"]],
    ["Fonte dos dados", i.fonte],
    ["Periodicidade", i.periodicidade],
    ["Responsável", i.responsavel],
  ];
  return (
    <details className="group rounded-lg border bg-muted/30 px-4 py-3 [&_summary::-webkit-details-marker]:hidden">
      <summary className="flex cursor-pointer list-none items-center justify-between gap-2 text-sm font-medium">
        Ficha do indicador: fórmula, fonte, periodicidade e responsável
        <ArrowRight className="size-4 transition-transform group-open:rotate-90" aria-hidden="true" />
      </summary>
      <dl className="m-0 mt-3 grid gap-x-6 gap-y-3 text-sm sm:grid-cols-2">
        {linhas
          .filter(([, v]) => v)
          .map(([r, v]) => (
            <div key={r} className="flex flex-col gap-0.5">
              <dt className="text-xs font-medium text-muted-foreground">{r}</dt>
              <dd className="m-0">{v}</dd>
            </div>
          ))}
      </dl>
    </details>
  );
}

/** Aba Indicadores: um indicador do núcleo em detalhe, com os dados de origem. */
export default async function Indicadores({ searchParams }: Props) {
  const { i: pedido } = await searchParams;
  const execucao = await getExecucao({ conjunto: "nucleo" });
  const inds = execucao.indicadores;
  const i = inds.find((x) => x.codigo === pedido) ?? inds.find((x) => x.codigo === "N01") ?? inds[0];
  const p = i.projecao;
  const ano = p?.ano ?? new Date().getFullYear();
  const serie = completos(i);
  const ult = serie.at(-1);
  const v = variacao(i);
  const assoc = DADOS_ASSOCIADOS[i.codigo];
  // um fetch por painel temático usado; cada gráfico junta as partes, só nos subtemas do indicador
  const slugs = [...new Set(assoc?.graficos.flatMap((g) => g.partes.map((pt) => pt.slug)) ?? [])];
  const paineis = new Map<string, Painel>();
  await Promise.all(
    slugs.map(async (slug) => {
      const pn = await getPainel(slug, { granularidade: "mes", valor: "real", ano_inicio: String(ano - 1) }).catch(() => null);
      if (pn) paineis.set(slug, pn);
    }),
  );
  const graficos = (assoc?.graficos ?? [])
    .map((g) => ({
      titulo: g.titulo,
      pontos: g.partes.flatMap((pt): PontoSerie[] =>
        (paineis.get(pt.slug)?.series ?? []).filter(
          (x) => x.metrica === pt.metrica && (!pt.subtemas || (x.grupo != null && pt.subtemas.includes(x.grupo))),
        ),
      ),
    }))
    .filter((g) => g.pontos.length);
  const emReais = assoc?.graficos.some((g) => g.partes.some((pt) => pt.metrica === "pago" || pt.metrica.startsWith("empenhado")));
  const doEixo = inds.filter((x) => x.eixo_pls === i.eixo_pls);
  const historico = (i.historico ?? []).filter((h) => h.valor != null);

  return (
    <main className="mx-auto flex max-w-280 flex-col gap-8 px-4 py-10">
      <header className="flex max-w-3xl flex-col gap-2">
        <h1 className="m-0 text-3xl font-bold tracking-tight">Análise por indicador</h1>
        <p className="m-0 text-muted-foreground">
          Cada indicador do núcleo em detalhe: o que mede, como é calculado, a série anual, a execução de {ano} e os dados de
          origem (consumo, gasto, combustível) que o compõem.
        </p>
      </header>

      <Card size="sm">
        <CardContent className="flex flex-col gap-4">
          <div className="flex flex-col gap-2">
            <p className="m-0 text-sm font-medium">1. Escolha o eixo</p>
            <PilulasEixos
              indicadores={inds}
              atual={i.eixo_pls}
              href={(e) => `/pls/indicadores?i=${inds.filter((x) => x.eixo_pls === e).sort((a, b) => a.codigo.localeCompare(b.codigo))[0].codigo}`}
            />
          </div>
          <div className="flex flex-col gap-2 border-t pt-4">
            <p className="m-0 text-xs font-semibold tracking-wider text-muted-foreground uppercase">
              2. Escolha o indicador · {rotuloEixo(i.eixo_pls)}: {nomeEixo(i.eixo_pls)}
            </p>
            <PilulasLink
              rotulo="Indicadores do eixo"
              itens={doEixo.map((x) => ({
                href: `/pls/indicadores?i=${x.codigo}`,
                texto: `${x.codigo} · ${x.indicador}${complementar(x) ? " (complementar)" : ""}`,
                ativo: x.codigo === i.codigo,
              }))}
            />
          </div>
        </CardContent>
      </Card>

      <section aria-labelledby="ind-titulo" className="flex flex-col gap-5">
        <div className="flex flex-wrap items-start gap-3">
          <Medalhao icone={ICONE_INDICADOR[i.codigo]} tom={TOM_EIXO[i.eixo_pls]} grande />
          <div className="flex min-w-0 flex-1 flex-col gap-1">
            <span className="text-xs font-semibold tracking-wider text-muted-foreground uppercase tabular-nums">
              {i.codigo} · {rotuloEixo(i.eixo_pls)} · {i.unidade}
            </span>
            <h2 id="ind-titulo" className="m-0 text-2xl font-bold tracking-tight">
              {i.indicador}
            </h2>
            {i.o_que_mede && <p className="m-0 max-w-3xl text-muted-foreground">{i.o_que_mede}</p>}
          </div>
          <div className="flex items-center gap-2">
            <Badge variant={i.automacao === "informado" ? "outline" : "secondary"}>
              {i.automacao === "informado" ? "Informado pelo setor" : "Automático"}
            </Badge>
            {p && <SituacaoBadge situacao={p.situacao_projecao} />}
            <SelosGrupo i={i} />
          </div>
        </div>
        <Ficha i={i} />
        <DecisoesComissao decisoes={i.decisoes} />

        <dl className="m-0 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {[
            { r: ult ? `Apurado em ${ult.ano}` : "Último ano completo", v: fmt(ult?.valor, i.unidade), n: v ? `${v.texto} vs ${v.ano}` : "sem ano anterior" },
            {
              r: p?.metodo === "fotografia" ? `Posição em ${ano}` : `Acumulado ${ano}`,
              v: fmt(p?.valor_parcial, i.unidade),
              n: p?.metodo === "fotografia" ? "data do acompanhamento" : periodo(p?.meses) ?? "sem dado no ano",
            },
            { r: `Projeção ${ano}`, v: fmt(p?.projecao, i.unidade), n: p ? comoProjetou(p).split(":")[0].split(" (")[0] : "" },
            { r: `Meta ${ano} (proposta)`, v: textoMeta(i), n: p ? regraMeta(p, i.unidade) : "" },
          ].map((k) => (
            <Card key={k.r} size="sm">
              <CardContent>
                <Dado rotulo={k.r} valor={k.v} nota={k.n} forte />
              </CardContent>
            </Card>
          ))}
        </dl>

        <div className="grid gap-4 lg:grid-cols-[minmax(0,1.7fr)_minmax(0,1fr)]">
          <Card>
            <CardHeader>
              <CardTitle>Evolução anual</CardTitle>
              <CardDescription>Anos completos, projeção de {ano} e meta proposta para o ano.</CardDescription>
            </CardHeader>
            <CardContent>
              {serie.length || p?.projecao != null ? (
                <EvolucaoChart serie={serie} unidade={i.unidade} ano={ano} projecao={p?.projecao ?? null} meta={p?.meta_projetada ?? null} altura={300} />
              ) : (
                <p className="m-0 text-sm text-muted-foreground">Sem série apurada: aguarda a informação do setor responsável.</p>
              )}
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>Execução de {ano}</CardTitle>
              <CardDescription>Proposta de meta, a validar pela Comissão do PLS.</CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col gap-4 text-sm">
              <BarraAlcance i={i} />
              {p && (
                <>
                  <p className="m-0">
                    <span className="font-medium">Meta: </span>
                    {textoMeta(i)}{p.regra !== "minimo" && ` (${regraMeta(p, i.unidade)})`}. {p.fundamento}.
                  </p>
                  <p className="m-0">
                    <span className="font-medium">Projeção: </span>
                    {comoProjetou(p)}
                  </p>
                </>
              )}
              {historico.length > 0 && (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Ano</TableHead>
                      <TableHead className="text-right">Valor</TableHead>
                      <TableHead>Situação do ano</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {historico.map((h) => (
                      <TableRow key={h.ano}>
                        <TableCell className="tabular-nums">{h.ano}</TableCell>
                        <TableCell className="text-right tabular-nums">{fmt(h.valor, i.unidade)}</TableCell>
                        <TableCell className="text-muted-foreground">{h.ano_completo ? "completo" : h.ano === ano ? "em curso" : "incompleto"}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </div>
      </section>

      <section aria-labelledby="assoc-titulo" className="flex flex-col gap-4">
        <div className="flex max-w-3xl flex-col gap-1">
          <h2 id="assoc-titulo" className="m-0 text-xl font-bold tracking-tight">
            Dados associados
          </h2>
          <p className="m-0 text-muted-foreground">
            {assoc
              ? `${assoc.texto} Série mensal de ${ano - 1} e ${ano}${emReais ? "; valores em R$ corrigidos pelo IPCA" : ""}.`
              : SEM_PAINEL[i.codigo] ?? "Os dados vêm direto da fonte descrita na ficha do indicador."}
          </p>
        </div>
        {graficos.length > 0 && (
          <div className="grid gap-4 lg:grid-cols-2">
            {graficos.map((g) => (
              <Card key={g.titulo}>
                <CardHeader>
                  <CardTitle className="text-base">{g.titulo}</CardTitle>
                </CardHeader>
                <CardContent>
                  <SerieChart pontos={g.pontos} perCapita={false} />
                </CardContent>
              </Card>
            ))}
          </div>
        )}
        {slugs.some((slug) => !FORA_DA_NAVEGACAO.has(slug)) && (
          <p className="m-0 flex flex-wrap gap-x-4 gap-y-1 text-sm">
            {slugs.filter((slug) => !FORA_DA_NAVEGACAO.has(slug)).map((slug) => (
              <Link key={slug} href={`/pls/${slug}`} className="flex items-center gap-1 font-medium text-primary">
                Painel de {paineis.get(slug)?.label.toLowerCase() ?? slug} completo <ArrowRight className="size-4" aria-hidden="true" />
              </Link>
            ))}
          </p>
        )}
      </section>
    </main>
  );
}
