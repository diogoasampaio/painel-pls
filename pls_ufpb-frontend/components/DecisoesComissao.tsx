import { Scale } from "lucide-react";
import type { Decisao } from "@/lib/api";
import { cn } from "@/lib/utils";

/** "(a) ... (b) ..." -> itens da lista de opcoes. */
function opcoes(texto: string | null): string[] {
  if (!texto) return [];
  const partes = texto.split(/\s*(?=\([a-z]\)\s)/).map((p) => p.trim()).filter(Boolean);
  return partes.length ? partes : [texto];
}

/**
 * Questões em aberto para a Comissão do PLS sobre o indicador (ref/decisoes_comissao.csv no ETL):
 * a pergunta, o contexto, as opções e o efeito de cada uma no número. Decidida, mostra a decisão.
 */
export function DecisoesComissao({ decisoes, compacto }: { decisoes?: Decisao[] | null; compacto?: boolean }) {
  const lista = decisoes ?? [];
  if (!lista.length) return null;
  const pendentes = lista.filter((d) => d.situacao === "pendente").length;
  return (
    <section
      aria-label="Decisões da Comissão do PLS"
      className="flex flex-col gap-3 rounded-lg border border-warning/60 bg-warning/10 px-4 py-3"
    >
      <p className="m-0 flex items-center gap-2 text-sm font-semibold">
        <Scale className="size-4 shrink-0" aria-hidden="true" />
        {pendentes
          ? `${pendentes === 1 ? "Decisão pendente" : `${pendentes} decisões pendentes`} da Comissão do PLS`
          : "Decisões da Comissão do PLS"}
      </p>
      <ol className="m-0 flex list-none flex-col gap-4 p-0">
        {lista.map((d) => (
          <li key={d.id} className={cn("flex flex-col gap-1.5 text-sm", d.situacao !== "pendente" && "opacity-80")}>
            <p className="m-0 font-medium">
              <span className="mr-1.5 text-xs text-muted-foreground tabular-nums">{d.id}</span>
              {d.questao}
            </p>
            {!compacto && d.contexto && <p className="m-0 text-muted-foreground">{d.contexto}</p>}
            {!compacto && opcoes(d.opcoes).length > 0 && (
              <ul className="m-0 flex list-none flex-col gap-1 p-0">
                {opcoes(d.opcoes).map((o) => (
                  <li key={o} className="rounded-md bg-card/70 px-2.5 py-1.5">
                    {o}
                  </li>
                ))}
              </ul>
            )}
            {!compacto && d.efeito && (
              <p className="m-0 text-xs text-muted-foreground">
                <span className="font-medium text-foreground">Efeito no indicador: </span>
                {d.efeito}
              </p>
            )}
            {d.situacao !== "pendente" && d.decisao && (
              <p className="m-0 text-xs">
                <span className="font-medium">Decisão: </span>
                {d.decisao}
              </p>
            )}
          </li>
        ))}
      </ol>
    </section>
  );
}
