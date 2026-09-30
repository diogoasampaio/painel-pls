import { Seletor } from "@/components/Seletor";
import type { Granularidade, Valor } from "@/lib/api";
import { VALOR_LABEL } from "@/lib/format";

/** Valor (R$ constantes, correntes, por pessoa, por m²) e granularidade, na URL. */
export function Controles({ base, valor, granularidade }: { base: string; valor: Valor; granularidade: Granularidade }) {
  const href = (v: Valor, g: Granularidade) => `${base}?valor=${v}&granularidade=${g}`;
  return (
    <div className="mb-5 flex flex-wrap gap-3 *:max-w-full *:min-w-0">
      <Seletor
        rotulo="Valor"
        atual={valor}
        opcoes={(Object.keys(VALOR_LABEL) as Valor[]).map((v) => ({ valor: v, texto: VALOR_LABEL[v], href: href(v, granularidade) }))}
      />
      <Seletor
        rotulo="Período"
        atual={granularidade}
        opcoes={(["ano", "mes"] as Granularidade[]).map((g) => ({
          valor: g,
          texto: g === "ano" ? "Anual" : "Mensal",
          href: href(valor, g),
        }))}
      />
    </div>
  );
}
