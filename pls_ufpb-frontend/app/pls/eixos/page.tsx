import { CartaoExecucao } from "@/components/CartaoExecucao";
import { BarraSituacoes, complementar, ICONE_EIXO, Medalhao, PilulasEixos, TOM_EIXO } from "@/components/Nucleo";
import { Card, CardContent } from "@/components/ui/card";
import { getExecucao, getMetas } from "@/lib/api";
import { EIXOS, nomeEixo, rotuloEixo, SITUACAO } from "@/lib/pls";

export const dynamic = "force-dynamic";

type Props = { searchParams: Promise<{ eixo?: string }> };

/** Aba Eixos: os indicadores do núcleo de um eixo, com a evolução e a execução do ano frente à meta projetada. */
export default async function Eixos({ searchParams }: Props) {
  const { eixo: pedido } = await searchParams;
  const [execucao, metas] = await Promise.all([getExecucao({ conjunto: "nucleo" }), getMetas({}).catch(() => null)]);
  const inds = execucao.indicadores;
  const eixo = EIXOS.some((e) => e.codigo === pedido && inds.some((i) => i.eixo_pls === pedido)) ? pedido! : "1";
  const doEixo = inds
    .filter((i) => i.eixo_pls === eixo)
    .sort((a, b) => a.codigo.localeCompare(b.codigo));
  const descricao =
    eixo === "transversal"
      ? "Acompanhamento do próprio plano: ações cumpridas, em dia ou em andamento dentro do prazo, com evidência dos responsáveis."
      : metas?.eixos.find((e) => e.eixo_pls === eixo)?.descricao;
  const ano = inds.find((i) => i.projecao)?.projecao?.ano;

  return (
    <main className="mx-auto flex max-w-280 flex-col gap-8 px-4 py-10">
      <header className="flex max-w-3xl flex-col gap-2">
        <h1 className="m-0 text-3xl font-bold tracking-tight">Eixos do PLS</h1>
        <p className="m-0 text-muted-foreground">
          Os indicadores do núcleo organizados pelos eixos do PLS UFPB 2025–2029. Cada um traz a evolução anual e a
          execução de {ano}: a projeção do ano, a partir dos meses já apurados, frente a uma meta anual proposta, a validar
          pela Comissão do PLS.
        </p>
      </header>

      <Card size="sm">
        <CardContent className="flex flex-col gap-3">
          <p className="m-0 text-sm font-medium">Escolha o eixo</p>
          <PilulasEixos indicadores={inds} atual={eixo} href={(e) => `/pls/eixos?eixo=${e}`} />
        </CardContent>
      </Card>

      <section aria-labelledby="eixo-titulo" className="flex flex-col gap-5">
        <div className="flex flex-wrap items-start justify-between gap-6">
          <div className="flex max-w-2xl items-start gap-3">
            <Medalhao icone={ICONE_EIXO[eixo]} tom={TOM_EIXO[eixo]} grande />
            <div className="flex flex-col gap-1">
              <span className="text-xs font-semibold tracking-wider text-muted-foreground uppercase">{rotuloEixo(eixo)}</span>
              <h2 id="eixo-titulo" className="m-0 text-2xl font-bold tracking-tight">
                {nomeEixo(eixo)}
              </h2>
              {descricao && <p className="m-0 text-sm text-muted-foreground">{descricao}</p>}
            </div>
          </div>
          <div className="flex w-full max-w-sm flex-col gap-2">
            <p className="m-0 text-xs font-medium text-muted-foreground">
              {doEixo.length} {doEixo.length === 1 ? "indicador" : "indicadores"} · situação em {ano}
            </p>
            <BarraSituacoes indicadores={doEixo} />
          </div>
        </div>
        <div className="flex flex-col gap-4">
          {doEixo.filter((i) => !complementar(i)).map((i) => (
            <CartaoExecucao key={i.codigo} i={i} />
          ))}
        </div>
        {doEixo.some(complementar) && (
          <div className="flex flex-col gap-4">
            <h3 className="m-0 border-t pt-5 text-lg font-semibold">
              Indicadores complementares <span className="text-sm font-normal text-muted-foreground">· metas do PLS medidas com os dados de compras e pedidos</span>
            </h3>
            {doEixo.filter(complementar).map((i) => (
              <CartaoExecucao key={i.codigo} i={i} />
            ))}
          </div>
        )}
      </section>

      <p className="m-0 text-xs text-muted-foreground">
        Situação do ano: {SITUACAO.no_rumo.texto.toLowerCase()} = a projeção cumpre a meta; {SITUACAO.atencao.texto.toLowerCase()} =
        a até 10% da meta (na faixa de manutenção, até 1,5 vez a tolerância); {SITUACAO.fora_do_rumo.texto.toLowerCase()} = além
        disso. As regras das metas projetadas estão em <code>ref/metas_2026_projecao.csv</code> no ETL.
      </p>
    </main>
  );
}
