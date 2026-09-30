import Link from "next/link";
import { ArrowRight, Layers, TrendingUp } from "lucide-react";
import { HeroSustentabilidade } from "@/components/HeroSustentabilidade";
import { BarraSituacoes, complementar, ICONE_INDICADOR, Medalhao, TOM_EIXO } from "@/components/Nucleo";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { getExecucao } from "@/lib/api";
import { completos, EIXOS, fmt, MESES_LONGOS, rotuloEixo, SITUACAO, variacao, type Ind } from "@/lib/pls";
import { cn } from "@/lib/utils";

export const dynamic = "force-dynamic";

const pct = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 1 });

function Secao({ id, titulo, descricao, children }: { id: string; titulo: string; descricao?: React.ReactNode; children: React.ReactNode }) {
  return (
    <section id={id} aria-labelledby={`${id}-titulo`} className="flex scroll-mt-20 flex-col gap-5">
      <div className="flex max-w-3xl flex-col gap-1">
        <h2 id={`${id}-titulo`} className="m-0 text-2xl font-bold tracking-tight">
          {titulo}
        </h2>
        {descricao && <p className="m-0 text-muted-foreground">{descricao}</p>}
      </div>
      {children}
    </section>
  );
}

/** Valor de destaque de cada indicador: último ano completo; sem ano completo, a posição do ano em curso. */
function destaque(i: Ind): { valor: number; ano: number; parcial: boolean } | null {
  const c = completos(i).at(-1);
  if (c) return { ...c, parcial: false };
  if (i.ultimo) return { valor: i.ultimo.valor, ano: i.ultimo.ano, parcial: true };
  return null;
}

/** Cartão de número do núcleo (como os do SAEGO): eixo, indicador (ano), valor, variação e situação do ano corrente. */
function CartaoNumero({ i }: { i: Ind }) {
  const d = destaque(i);
  const v = variacao(i);
  const eixo = EIXOS.find((e) => e.codigo === i.eixo_pls);
  const sit = i.projecao && i.projecao.situacao_projecao !== "sem_dado" ? SITUACAO[i.projecao.situacao_projecao] : null;
  return (
    <Link
      href={`/pls/indicadores?i=${i.codigo}`}
      className="group block h-full rounded-xl text-foreground no-underline outline-none focus-visible:ring-3 focus-visible:ring-ring/50"
    >
      <Card size="sm" className="h-full gap-3 transition-shadow group-hover:shadow-md group-hover:ring-primary/40">
        <CardHeader className="gap-2">
          <div className="flex items-center gap-2">
            <Medalhao icone={ICONE_INDICADOR[i.codigo]} tom={TOM_EIXO[i.eixo_pls]} />
            <span className="truncate text-[0.7rem] font-semibold tracking-wider text-muted-foreground uppercase">
              {i.eixo_pls === "transversal" ? "Gestão do plano" : `${rotuloEixo(i.eixo_pls)} · ${eixo?.curto}`}
            </span>
          </div>
          <CardTitle className="text-sm leading-snug font-semibold">
            {i.indicador}{" "}
            {d && (
              <span className="font-normal text-muted-foreground">
                ({d.ano}
                {d.parcial ? ", em curso" : ""})
              </span>
            )}
          </CardTitle>
        </CardHeader>
        <CardContent className="mt-auto flex flex-col gap-1.5">
          <p className="m-0 text-2xl font-semibold tracking-tight tabular-nums">{d ? fmt(d.valor, i.unidade) : "—"}</p>
          <p className="m-0 flex flex-wrap items-center justify-between gap-x-2 gap-y-1 text-xs">
            {v ? (
              <span className={cn("font-medium", v.bom == null ? "text-muted-foreground" : v.bom ? "text-success" : "text-destructive")}>
                {v.texto} <span className="font-normal text-muted-foreground">vs {v.ano}</span>
              </span>
            ) : (
              <span className="text-muted-foreground">{d ? "sem ano anterior" : "aguarda o setor"}</span>
            )}
            {sit && (
              <span className="flex items-center gap-1 text-muted-foreground">
                <span className={cn("size-2 rounded-full", sit.barra)} aria-hidden="true" />
                <span className="sr-only">{i.projecao!.ano}: </span>
                {sit.texto}
              </span>
            )}
          </p>
        </CardContent>
      </Card>
    </Link>
  );
}

/** Síntese automática da execução do ano corrente, para a gestão. */
function leitura(indicadores: Ind[], ano: number | undefined) {
  const com = indicadores.filter((i) => i.projecao && i.projecao.situacao_projecao !== "sem_dado");
  const por = (s: string) => com.filter((i) => i.projecao!.situacao_projecao === s);
  const nomes = (l: Ind[]) => l.map((i) => `${i.indicador.charAt(0).toLowerCase()}${i.indicador.slice(1)} (${i.codigo})`).join("; ");
  const meses = com.map((i) => i.projecao!.meses).filter((m): m is number => !!m);
  const freq = (m: number) => meses.filter((x) => x === m).length;
  const moda = meses.length ? [...meses].sort((a, b) => freq(b) - freq(a) || b - a)[0] : null;
  const semDado = indicadores.filter((i) => !i.projecao || i.projecao.situacao_projecao === "sem_dado");
  const ate = moda ? MESES_LONGOS[moda - 1] : null;
  const frases = [
    `Em ${ano}, com dados até ${ate ?? "o último mês carregado"} na maior parte das fontes, ${por("no_rumo").length} dos ${com.length} indicadores com projeção estão no rumo da meta projetada, ${por("atencao").length} pedem atenção e ${por("fora_do_rumo").length} estão fora do rumo.`,
  ];
  if (por("no_rumo").length) frases.push(`No rumo: ${nomes(por("no_rumo"))}.`);
  if (por("atencao").length) frases.push(`Atenção, a até 10% da meta: ${nomes(por("atencao"))}.`);
  if (por("fora_do_rumo").length) frases.push(`Fora do rumo: ${nomes(por("fora_do_rumo"))}.`);
  if (semDado.length) frases.push(`Sem dado para projetar: ${nomes(semDado)}.`);
  return frases;
}

/** Visão geral: hero, índice sintético, execução do ano, os 15 números e a leitura executiva. */
export default async function VisaoGeral() {
  const execucao = await getExecucao({ conjunto: "nucleo" }).catch(() => null);
  const inds = execucao?.indicadores ?? [];
  const atual = execucao?.serie.find((s) => s.ano === execucao.ano);
  const fechado = execucao?.serie.filter((s) => s.ano_fechado && s.indice_sintetico != null).at(-1);
  const anoProj = inds.find((i) => i.projecao)?.projecao?.ano;
  const anosDados = inds.flatMap((i) => (i.historico ?? []).filter((h) => h.ano_completo).map((h) => h.ano));
  const anos: [number, number] | null = anosDados.length ? [Math.min(...anosDados), anoProj ?? Math.max(...anosDados)] : null;
  const automaticos = inds.filter((i) => i.automacao !== "informado").length;
  const principais = inds.filter((i) => !complementar(i));
  const complementares = inds.filter(complementar);

  return (
    <>
      <HeroSustentabilidade
        indicadores={principais.length || 15}
        complementares={complementares.length}
        indice={fechado?.indice_sintetico ?? null}
        anoIndice={fechado?.ano ?? null}
        anos={anos}
      />
      <main className="mx-auto flex max-w-280 flex-col gap-14 px-4 py-12">
        <Secao
          id="panorama"
          titulo="Panorama do PLS"
          descricao={
            <>
              {principais.length} indicadores do núcleo e {complementares.length} complementares · {automaticos} apurados
              automaticamente · 6 eixos e a gestão do plano
              {anos && ` · dados de ${anos[0]} a ${anos[1]}`}
            </>
          }
        >
          <div className="grid gap-4 lg:grid-cols-5">
            <Card className="lg:col-span-3">
              <CardHeader>
                <CardDescription>Indicador sintético</CardDescription>
                <CardTitle className="text-lg">Índice de execução do PLS</CardTitle>
              </CardHeader>
              <CardContent className="flex flex-col gap-5">
                <div className="flex flex-wrap items-end gap-x-10 gap-y-4">
                  {fechado && (
                    <p className="m-0 flex flex-col">
                      <span className="text-5xl font-bold tracking-tight text-primary tabular-nums">{pct.format(fechado.indice_sintetico!)}%</span>
                      <span className="text-sm text-muted-foreground">em {fechado.ano}, último ano fechado</span>
                    </p>
                  )}
                  {atual && atual.ano !== fechado?.ano && atual.indice_sintetico != null && (
                    <p className="m-0 flex max-w-64 flex-col">
                      <span className="text-3xl font-semibold tracking-tight tabular-nums">{pct.format(atual.indice_sintetico)}%</span>
                      <span className="text-sm text-muted-foreground">
                        {atual.ano}, em curso: metas de {atual.ano_metas ?? "—"}
                        {atual.indice_acoes != null && ` com as ações do ciclo (${pct.format(atual.indice_acoes)}%)`}
                      </span>
                    </p>
                  )}
                </div>
                {fechado && (
                  <div className="flex flex-col gap-1.5">
                    <div className="h-2.5 w-full overflow-hidden rounded-full bg-muted" aria-hidden="true">
                      <div className="h-full rounded-full bg-primary" style={{ width: `${Math.min(100, fechado.indice_sintetico!)}%` }} />
                    </div>
                    <p className="m-0 text-sm text-muted-foreground">
                      Média do alcance das metas por eixo. Em {fechado.ano}, {fechado.n_avaliados} de {fechado.n_com_meta} indicadores
                      com meta definida no PLS foram avaliados.
                    </p>
                  </div>
                )}
                <Link href="/pls/nucleo" className="flex items-center gap-1 text-sm font-medium text-primary">
                  Como o índice é calculado <ArrowRight className="size-4" aria-hidden="true" />
                </Link>
              </CardContent>
            </Card>
            <Card className="lg:col-span-2">
              <CardHeader>
                <CardDescription>Execução em {anoProj ?? "curso"}</CardDescription>
                <CardTitle className="text-lg">Indicadores frente à meta projetada</CardTitle>
              </CardHeader>
              <CardContent className="flex flex-col gap-4">
                <BarraSituacoes indicadores={inds} />
                <p className="m-0 text-sm text-muted-foreground">
                  Projeção do ano a partir dos meses já carregados, comparada a uma meta anual para cada indicador.{" "}
                  <strong className="font-medium text-foreground">As metas projetadas são uma proposta, a validar pela Comissão do PLS.</strong>
                </p>
                <Link href="/pls/eixos" className="flex items-center gap-1 text-sm font-medium text-primary">
                  Ver por eixo <ArrowRight className="size-4" aria-hidden="true" />
                </Link>
              </CardContent>
            </Card>
          </div>
        </Secao>

        <Secao
          id="numeros"
          titulo="Principais números"
          descricao="Os 15 indicadores do núcleo no último ano completo, com a variação sobre o ano anterior (verde quando vai no sentido desejado) e a situação do ano em curso."
        >
          <ul className="m-0 grid list-none gap-3 p-0 sm:grid-cols-2 md:grid-cols-3 xl:grid-cols-5">
            {principais.map((i) => (
              <li key={i.codigo}>
                <CartaoNumero i={i} />
              </li>
            ))}
          </ul>
          <p className="m-0 text-xs text-muted-foreground">
            As fontes fecham o ano em momentos diferentes: o ano de cada número está entre parênteses. A situação ao pé do
            cartão é a de {anoProj}, frente à meta projetada.
          </p>
        </Secao>

        {complementares.length > 0 && (
          <Secao
            id="complementares"
            titulo="Indicadores complementares"
            descricao="Materiais adquiridos (copos, papel, toner), combustível fóssil, Almoxarifado Virtual Nacional e critérios nos editais: metas do PLS que o painel passou a medir com os dados de compras e pedidos. Os que têm meta entram no índice sintético."
          >
            <ul className="m-0 grid list-none gap-3 p-0 sm:grid-cols-2 md:grid-cols-3 xl:grid-cols-4">
              {complementares.map((i) => (
                <li key={i.codigo}>
                  <CartaoNumero i={i} />
                </li>
              ))}
            </ul>
          </Secao>
        )}

        <Secao id="leitura" titulo="Leitura executiva" descricao="Síntese automática da execução do ano em curso, para apoio à gestão.">
          <Card>
            <CardContent className="flex max-w-4xl flex-col gap-3 text-sm leading-relaxed">
              {leitura(inds, anoProj).map((f) => (
                <p key={f} className="m-0">
                  {f}
                </p>
              ))}
              <p className="m-0 text-muted-foreground">
                As metas do ano são uma projeção técnica a partir das metas do PLS 2025–2029 e da linha de base de cada
                indicador, a validar pela Comissão. Leia os números com o contexto de cada unidade: expansão de área, obras,
                mudanças de contrato e sazonalidade do calendário acadêmico.
              </p>
            </CardContent>
          </Card>
          <div className="flex flex-wrap gap-3">
            <Link href="/pls/eixos" className={cn(buttonVariants({ size: "lg" }), "h-11 px-5 text-primary-foreground no-underline")}>
              <Layers data-icon="inline-start" aria-hidden="true" />
              Explorar os eixos
            </Link>
            <Link href="/pls/indicadores" className={cn(buttonVariants({ size: "lg", variant: "outline" }), "h-11 px-5 text-foreground no-underline")}>
              <TrendingUp data-icon="inline-start" aria-hidden="true" />
              Detalhar um indicador
            </Link>
          </div>
        </Secao>

        <Secao id="sobre-pls" titulo="O que é o PLS">
          <div className="grid gap-6 md:grid-cols-2">
            <div className="flex flex-col gap-3 text-base">
              <p className="m-0">
                O <strong>Plano de Logística Sustentável (PLS)</strong> é o instrumento com que a UFPB planeja, executa e
                acompanha práticas de sustentabilidade e de racionalização de gastos, como exige a Portaria SEGES/ME nº
                8.678/2021 para a administração pública federal.
              </p>
              <p className="m-0 text-muted-foreground">
                O plano 2025–2029 organiza objetivos, metas, ações e responsáveis em seis eixos. Este painel apura o núcleo de
                15 indicadores a partir de fontes públicas e dos registros dos setores.
              </p>
            </div>
            <Card size="sm">
              <CardHeader>
                <CardTitle>Como os dados chegam ao painel</CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="m-0 flex list-disc flex-col gap-2 pl-5 text-sm text-muted-foreground">
                  <li>Despesas e pagamentos do Portal da Transparência, corrigidos pelo IPCA.</li>
                  <li>Faturas de energia, água, combustível e resíduos anexadas aos processos no SIPAC.</li>
                  <li>Contagem da comunidade acadêmica da UFPB (discentes, docentes, técnicos e terceirizados) para os indicadores por pessoa.</li>
                  <li>Formulários dos setores responsáveis para o que não está em dados públicos.</li>
                </ul>
              </CardContent>
            </Card>
          </div>
        </Secao>

        <nav aria-label="Gestão do painel" className="flex flex-wrap items-center gap-2 border-t pt-6 text-sm text-muted-foreground">
          <span>Mais do painel:</span>
          <Link href="/pls/indicadores-globais">Gasto e consumo por tema</Link>
          <span aria-hidden="true">·</span>
          <Link href="/pls/nucleo">Índice e faixas</Link>
          <span aria-hidden="true">·</span>
          <Link href="/pls/formularios">Formulários dos setores</Link>
          <span aria-hidden="true">·</span>
          <Link href="/pls/saude">Saúde da carga</Link>
        </nav>
      </main>
    </>
  );
}
