"use client";

import { CardStat } from "@/components/ui/ds-card-stat";
import type { Destaque } from "@/lib/api";
import { formatValor } from "@/lib/format";
import { cn } from "@/lib/utils";

const pct = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 1, signDisplay: "exceptZero" });

/**
 * Pago no último ano completo x o ano imediatamente anterior, com o ds-card-stat
 * do LEMA-DS (o componente não tem opção de polaridade, então a cor vem de uma
 * classe na grade, em globals.css):
 *   menor   queda de gasto é o resultado desejado (energia, água, material,
 *           deslocamento): .polaridade-menor-melhor troca success e destructive
 *   neutro  gasto sem sentido desejado (vigilância, alimentação, treinamento):
 *           .polaridade-neutra pinta alta e queda de cinza; a seta continua
 */
export function Destaques({
  itens,
  rotulos,
  perCapita,
  polaridade = "menor",
  valor,
}: {
  itens: Destaque[];
  rotulos?: Record<string, string>;
  perCapita: boolean;
  polaridade?: "menor" | "neutro";
  /** rótulo do tipo de valor no título (ex.: "R$ constantes (IPCA)") */
  valor?: string;
}) {
  if (!itens.length) return null;
  const anos = [...new Set(itens.map((d) => d.ano))];
  return (
    <section aria-labelledby="destaques-titulo" className="mb-6 flex flex-col gap-3">
      <h2 id="destaques-titulo" className="m-0 text-base font-semibold">
        Pago em {anos.length === 1 ? anos[0] : "cada último ano com pagamento"}
        <span className="font-normal text-muted-foreground">
          {" "}
          · último ano completo{valor ? `, ${valor}` : ""}, comparado ao ano anterior
        </span>
      </h2>
      <div
        className={cn(
          polaridade === "neutro" ? "polaridade-neutra" : "polaridade-menor-melhor",
          "grid grid-cols-[repeat(auto-fill,minmax(14rem,1fr))] gap-4",
        )}
      >
        {itens.map((d) => {
          const v = d.variacao_pct;
          const trend = v == null ? false : v < 0 ? "down" : v > 0 ? "up" : "neutral";
          const comparacao =
            v != null ? `${pct.format(v)}% vs ${d.ano_anterior}` : d.ano_anterior ? `sem pagamento em ${d.ano_anterior}` : "primeiro ano da série";
          return (
            <CardStat
              key={d.grupo ?? "total"}
              label={rotulos?.[d.grupo ?? ""] ?? d.grupo ?? "Total"}
              value={formatValor(d.valor, "R$", perCapita)}
              description={`Pago em ${d.ano} · ${comparacao}`}
              trend={trend}
              size="md"
              locale="pt-BR"
            />
          );
        })}
      </div>
    </section>
  );
}
