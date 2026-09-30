"use client";

import { LineChart } from "@/components/ui/ds-line-chart";
import { fmt } from "@/lib/pls";

/**
 * Evolução anual de um indicador do núcleo no ds-line-chart:
 *   Apurado        anos completos (linha cheia)
 *   Projeção AAAA  do último ano completo até a projeção do ano corrente (tracejada)
 *   Meta AAAA      meta projetada, reta tracejada em todos os anos
 * A meta vai como série, e não como referenceLine: o eixo do DS não se
 * estende até a linha de referência, e uma meta acima dos dados sumiria.
 */
export function EvolucaoChart({
  serie,
  unidade,
  ano,
  projecao,
  meta,
  altura = 220,
}: {
  serie: { ano: number; valor: number }[];
  unidade: string;
  ano: number;
  projecao: number | null;
  meta: number | null;
  altura?: number;
}) {
  const anos = [...new Set([...serie.map((s) => s.ano), ...(projecao != null || meta != null ? [ano] : [])])].sort();
  const ultimo = serie.at(-1);
  const kProj = `Projeção ${ano}`;
  const kMeta = `Meta ${ano} (proposta)`;
  const dados = anos.map((a) => {
    const linha: Record<string, string | number> = { ano: String(a) };
    const v = serie.find((s) => s.ano === a);
    if (v) linha.Apurado = v.valor;
    if (projecao != null && (a === ano || a === ultimo?.ano)) linha[kProj] = a === ano ? projecao : ultimo!.valor;
    if (meta != null) linha[kMeta] = meta;
    return linha;
  });
  const chaves = [
    { key: "Apurado", label: "Apurado (ano completo)", color: "var(--chart-1)" },
    ...(projecao != null ? [{ key: kProj, label: kProj, color: "var(--chart-2)", dashed: true }] : []),
    ...(meta != null ? [{ key: kMeta, label: kMeta, color: "var(--success)", dashed: true }] : []),
  ];
  return (
    <LineChart
      data={dados}
      categoryKey="ano"
      dataKeys={chaves}
      height={altura}
      dots="always"
      curve="linear"
      showLegend
      legendPosition="bottom"
      valueFormatter={(v) => fmt(v, unidade, true)}
      locale="pt-BR"
    />
  );
}
