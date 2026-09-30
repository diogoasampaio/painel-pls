import Link from "next/link";
import PainelExecucao from "@/components/Execucao";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/ds-badge";
import { getExecucao, type Execucao } from "@/lib/api";
import { FAIXA_COR } from "@/lib/faixas";
import { formatValor } from "@/lib/format";

export const dynamic = "force-dynamic";

const EIXOS: Record<string, string> = {
  "1": "Racionalização e consumo consciente",
  "2": "Ocupação dos espaços físicos",
  "3": "Objetos de menor impacto ambiental",
  "4": "Inovação no mercado",
  "5": "Negócios de impacto",
  "6": "Divulgação e capacitação",
  transversal: "Gestão do plano",
};

const AUTOMACAO: Record<string, string> = {
  automatizado: "Automatizado",
  calcular: "Dado coletado, falta calcular",
  fonte_nova: "Fonte pública nova (em integração)",
  informado: "Informado",
};

type Ind = Execucao["indicadores"][number];

function Cartao({ i, faixas }: { i: Ind; faixas: Execucao["faixas"] }) {
  const faixa = faixas.find((f) => f.codigo === i.faixa);
  const u = i.ultimo;
  return (
    <Card size="sm" id={i.codigo}>
      <CardHeader>
        <CardDescription className="flex flex-wrap items-center gap-2">
          {/* cor da faixa por token (lib/faixas.ts); className sobrepõe o fundo da variante */}
          <Badge className={FAIXA_COR[i.faixa]}>
            {faixa?.faixa ?? i.faixa}
            {i.alcance_pct != null && i.faixa !== "atingida" ? ` · ${i.alcance_pct.toFixed(0)}%` : ""}
          </Badge>
          {i.codigo} · {AUTOMACAO[i.automacao ?? ""] ?? i.automacao}
        </CardDescription>
        <CardTitle>{i.indicador}</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-2 text-sm">
        <p>
          {u ? (
            <>
              <span className="text-xl font-semibold tracking-tight tabular-nums">{formatValor(u.valor, i.unidade)}</span>{" "}
              <span className="text-muted-foreground">
                em {u.ano}
                {u.ano_completo === false ? " (parcial)" : ""}
              </span>
            </>
          ) : (
            <span className="text-muted-foreground">Sem valor ainda</span>
          )}
        </p>
        <p>
          <span className="text-muted-foreground">Meta:</span> {i.meta || <em className="text-muted-foreground">a definir pela Comissão</em>}
        </p>
        <details className="text-muted-foreground">
          <summary className="cursor-pointer">Fórmula, fonte e sugestão de meta</summary>
          <div className="mt-2 flex flex-col gap-2">
            <p>{i.formula}</p>
            <p>
              <span className="font-semibold">Fonte:</span> {i.fonte}
            </p>
            {i.meta_sugerida && (
              <p>
                <span className="font-semibold">Sugestão de meta:</span> {i.meta_sugerida}
              </p>
            )}
          </div>
        </details>
      </CardContent>
    </Card>
  );
}

/** Painel geral do PLS: indice sintetico de execucao e os 15 indicadores do nucleo. */
export default async function PainelPls() {
  const dados = await getExecucao({ conjunto: "nucleo" });
  const grupos = Object.keys(EIXOS).filter((e) => dados.indicadores.some((i) => i.eixo_pls === e));
  return (
    <main className="container">
      <h1 className="page-title">Painel do PLS</h1>
      <p className="caption">
        Os 15 indicadores do núcleo do PLS UFPB, que cobrem os seis temas obrigatórios da Portaria SEGES 8.678/2021, e o
        índice sintético que resume a execução do plano. O catálogo completo está em{" "}
        <Link href="/pls/metas">Metas do PLS 2025–2029</Link>.
      </p>
      <PainelExecucao dados={dados} />
      {grupos.map((e) => (
        <section key={e} className="mt-8 flex flex-col gap-4">
          <h2 className="section-title">
            {e === "transversal" ? "Transversal" : `Eixo ${e}`} · {EIXOS[e]}
          </h2>
          <div className="grid grid-cols-[repeat(auto-fill,minmax(min(100%,20rem),1fr))] gap-4">
            {dados.indicadores
              .filter((i) => i.eixo_pls === e)
              .map((i) => (
                <Cartao key={i.codigo} i={i} faixas={dados.faixas} />
              ))}
          </div>
        </section>
      ))}
    </main>
  );
}
