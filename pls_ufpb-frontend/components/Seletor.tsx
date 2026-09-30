"use client";

import { useRouter } from "next/navigation";
import { useTransition } from "react";
import { PillGroup } from "@/components/ui/ds-pill-group";

/**
 * ds-pill-group que navega: cada opcao e uma URL (query string), como eram os
 * links antes -- o estado continua na URL, compartilhavel. O pill-group e de
 * botoes (radiogroup), entao a escolha vira router.push. Quando as opcoes nao
 * cabem (celular), o DS rola na horizontal com esmaecimento na borda.
 */
export function Seletor({
  rotulo,
  opcoes,
  atual,
}: {
  rotulo: string;
  opcoes: { valor: string; texto: string; href: string }[];
  atual: string;
}) {
  const router = useRouter();
  const [carregando, iniciar] = useTransition();
  return (
    <PillGroup
      label={rotulo}
      items={opcoes.map((o) => ({ value: o.valor, label: o.texto }))}
      value={atual}
      onChange={(v) => {
        const o = opcoes.find((x) => x.valor === v);
        if (o && v !== atual) iniciar(() => router.push(o.href, { scroll: false }));
      }}
      aria-busy={carregando || undefined}
      size="sm"
      locale="pt-BR"
    />
  );
}
