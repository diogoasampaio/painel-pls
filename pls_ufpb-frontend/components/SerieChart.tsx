"use client";

import { BarChart } from "@/components/ui/ds-bar-chart";
import type { PontoSerie } from "@/lib/api";
import { formatEixo, formatValor } from "@/lib/format";

/** --chart-1..5 do LEMA-DS + --chart-6..10 do painel (app/globals.css): até 10 séries sem repetir cor. */
const N_CORES = 10;

/**
 * Barras empilhadas por grupo (subtema ou tema) ao longo do tempo, no
 * ds-bar-chart. O DS usa o mesmo formatador no eixo e no tooltip: valor
 * compacto ("R$ 11,8 mi"); por pessoa e por m², abaixo de R$ 100, com centavos
 * (R$ 3,75 viraria "R$ 3,8").
 */
export function SerieChart({
  pontos,
  rotulos,
  perCapita,
}: {
  pontos: PontoSerie[];
  rotulos?: Record<string, string>;
  perCapita: boolean;
}) {
  const unidade = pontos[0]?.unidade ?? null;
  const grupos = [...new Set(pontos.map((p) => p.grupo ?? "Total"))];
  const periodos = [...new Set(pontos.map((p) => p.periodo))].sort();
  const linhas = periodos.map((periodo) => {
    const linha: Record<string, string | number> = { periodo };
    for (const p of pontos.filter((x) => x.periodo === periodo)) {
      linha[p.grupo ?? "Total"] = p.valor ?? 0;
    }
    return linha;
  });

  return (
    <BarChart
      data={linhas}
      categoryKey="periodo"
      dataKeys={grupos.map((g, i) => ({ key: g, label: rotulos?.[g] ?? g, color: `var(--chart-${(i % N_CORES) + 1})` }))}
      stacked
      showLegend={grupos.length > 1}
      height={300}
      valueFormatter={(v) => (perCapita && v !== 0 && Math.abs(v) < 100 ? formatValor(v, unidade, true) : formatEixo(v, unidade))}
      locale="pt-BR"
    />
  );
}
