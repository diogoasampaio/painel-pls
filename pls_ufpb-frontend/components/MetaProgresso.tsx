"use client";

import { BulletChart } from "@/components/ui/ds-bullet-chart";

const num = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 1 });

/**
 * Valor x meta no ds-bullet-chart. Recebe so numeros (o formatador e uma
 * funcao e nao atravessa a fronteira server -> client). `percentual` fixa a
 * escala em 0-100; senao o eixo vai ate 115% do maior entre valor e meta.
 */
export function MetaProgresso({
  rotulo,
  valor,
  meta,
  percentual,
}: {
  rotulo: string;
  valor: number;
  meta: number;
  percentual: boolean;
}) {
  return (
    <BulletChart
      label={rotulo}
      value={valor}
      target={meta}
      max={percentual ? Math.max(100, valor, meta) : undefined}
      valueFormatter={(v) => (percentual ? `${num.format(v)}%` : num.format(v))}
      size="md"
      locale="pt-BR"
    />
  );
}
