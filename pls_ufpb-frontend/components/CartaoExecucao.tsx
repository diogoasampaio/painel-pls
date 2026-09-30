import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { DecisoesComissao } from "@/components/DecisoesComissao";
import { EvolucaoChart } from "@/components/EvolucaoChart";
import { ICONE_INDICADOR, Medalhao, SelosGrupo, SituacaoBadge, TOM_EIXO, textoMeta } from "@/components/Nucleo";
import { Card, CardContent } from "@/components/ui/card";
import { comoProjetou, completos, fmt, periodo, regraMeta, SITUACAO, variacao, type Ind } from "@/lib/pls";
import { cn } from "@/lib/utils";

/** Par rótulo/valor da coluna de números do cartão. */
export function Dado({ rotulo, valor, nota, forte }: { rotulo: string; valor: React.ReactNode; nota?: React.ReactNode; forte?: boolean }) {
  return (
    <div className="flex flex-col gap-0.5">
      <dt className="text-xs font-medium text-muted-foreground">{rotulo}</dt>
      <dd className={cn("m-0 tabular-nums", forte ? "text-xl font-semibold tracking-tight" : "text-base font-medium")}>{valor}</dd>
      {nota && <dd className="m-0 text-xs text-muted-foreground">{nota}</dd>}
    </div>
  );
}

/** Quanto da meta a projeção alcança (0–100), com a cor da situação. */
export function BarraAlcance({ i }: { i: Ind }) {
  const p = i.projecao;
  if (!p || p.alcance_projecao == null) return null;
  return (
    <div className="flex flex-col gap-1">
      <div className="h-2 w-full overflow-hidden rounded-full bg-muted" aria-hidden="true">
        <div className={cn("h-full rounded-full", SITUACAO[p.situacao_projecao].barra)} style={{ width: `${p.alcance_projecao}%` }} />
      </div>
      <p className="m-0 text-xs text-muted-foreground">
        A projeção alcança {new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 0 }).format(p.alcance_projecao)}% da meta
      </p>
    </div>
  );
}

/**
 * Indicador do núcleo na aba Eixos: evolução anual com a projeção e a meta do
 * ano corrente (gráfico) e, ao lado, último ano completo, acumulado do ano,
 * projeção, meta proposta e a situação.
 */
export function CartaoExecucao({ i }: { i: Ind }) {
  const p = i.projecao;
  const serie = completos(i);
  const ult = serie.at(-1);
  const v = variacao(i);
  const ano = p?.ano ?? new Date().getFullYear();
  return (
    <Card id={i.codigo} className="scroll-mt-20">
      <CardContent className="flex flex-col gap-5">
        <header className="flex flex-wrap items-start gap-3">
          <Medalhao icone={ICONE_INDICADOR[i.codigo]} tom={TOM_EIXO[i.eixo_pls]} grande />
          <div className="flex min-w-0 flex-1 flex-col gap-0.5">
            <span className="text-xs font-semibold tracking-wider text-muted-foreground uppercase tabular-nums">
              {i.codigo} · {i.unidade}
            </span>
            <h3 className="m-0 text-lg leading-snug font-semibold">{i.indicador}</h3>
            <SelosGrupo i={i} />
            {i.o_que_mede && <p className="m-0 max-w-3xl text-sm text-muted-foreground">{i.o_que_mede}</p>}
          </div>
          {p && <SituacaoBadge situacao={p.situacao_projecao} className="text-sm" />}
        </header>
        <div className="grid gap-6 lg:grid-cols-[minmax(0,1.7fr)_minmax(0,1fr)]">
          <div className="min-w-0">
            {serie.length || p?.projecao != null ? (
              <EvolucaoChart serie={serie} unidade={i.unidade} ano={ano} projecao={p?.projecao ?? null} meta={p?.meta_projetada ?? null} />
            ) : (
              <p className="m-0 flex h-full min-h-32 items-center justify-center rounded-lg border border-dashed text-sm text-muted-foreground">
                Sem série apurada: aguarda a informação do setor responsável.
              </p>
            )}
          </div>
          <div className="flex flex-col gap-4">
            <dl className="m-0 grid grid-cols-2 gap-x-4 gap-y-3">
              <Dado
                rotulo={ult ? `Apurado em ${ult.ano}` : "Último ano completo"}
                valor={fmt(ult?.valor, i.unidade)}
                nota={v ? `${v.texto} vs ${v.ano}` : undefined}
              />
              <Dado
                rotulo={p?.metodo === "fotografia" ? `Posição em ${ano}` : `Acumulado ${ano}`}
                valor={fmt(p?.valor_parcial, i.unidade)}
                nota={p?.metodo === "fotografia" ? "data do acompanhamento" : periodo(p?.meses) ?? undefined}
              />
              <Dado rotulo={`Projeção ${ano}`} valor={fmt(p?.projecao, i.unidade)} forte />
              <Dado rotulo={`Meta ${ano} (proposta)`} valor={textoMeta(i)} nota={p ? regraMeta(p, i.unidade) : undefined} forte />
            </dl>
            <BarraAlcance i={i} />
            {p && (
              <p className="m-0 text-xs text-muted-foreground">
                {comoProjetou(p)} {p.fundamento}.
              </p>
            )}
            <DecisoesComissao decisoes={i.decisoes} compacto />
            <Link href={`/pls/indicadores?i=${i.codigo}`} className="mt-auto flex items-center gap-1 text-sm font-medium text-primary">
              Detalhar indicador <ArrowRight className="size-4" aria-hidden="true" />
            </Link>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
