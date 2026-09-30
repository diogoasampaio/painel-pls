"use client";

import { CircleAlert, CircleCheck, CircleX, Clock } from "lucide-react";
import { CardStat } from "@/components/ui/ds-card-stat";

const ICONES = { relogio: Clock, erro: CircleX, atencao: CircleAlert, ok: CircleCheck };

/**
 * ds-card-stat para paginas server: o card usa o hook de idioma do DS (so no
 * navegador) e o icone e um componente, que nao atravessa a fronteira
 * server -> client -- por isso o icone vem pelo nome.
 */
export function Kpi({
  rotulo,
  valor,
  descricao,
  icone,
  destaque,
}: {
  rotulo: string;
  valor: string | number;
  descricao?: string;
  icone?: keyof typeof ICONES;
  /** classe de cor do valor (token do DS), ex.: text-destructive */
  destaque?: string;
}) {
  return (
    <CardStat
      label={rotulo}
      value={valor}
      description={descricao}
      icon={icone ? ICONES[icone] : undefined}
      valueClassName={destaque}
      size="md"
      locale="pt-BR"
    />
  );
}
