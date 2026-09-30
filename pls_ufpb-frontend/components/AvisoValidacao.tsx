import { TriangleAlert } from "lucide-react";

/**
 * Faixa de aviso no topo de todas as páginas enquanto o painel está em validação.
 * Liga/desliga por PAINEL_EM_VALIDACAO no .env (padrão: ligado; "nao" desliga).
 */
export function emValidacao() {
  return (process.env.PAINEL_EM_VALIDACAO ?? "sim").toLowerCase() !== "nao";
}

export function AvisoValidacao() {
  if (!emValidacao()) return null;
  return (
    <aside aria-label="Aviso: painel em validação" className="border-b border-warning/60 bg-warning/15">
      <div className="mx-auto flex max-w-280 items-start gap-3 px-4 py-3 text-sm">
        <TriangleAlert className="mt-0.5 size-5 shrink-0 text-warning-foreground" aria-hidden="true" />
        <p className="m-0 text-foreground">
          <strong className="font-semibold">Versão em validação.</strong> Os dados, indicadores e metas deste painel ainda
          estão sendo conferidos pela Comissão do PLS e pelos setores responsáveis. Os números podem mudar e não devem ser
          usados como resultado oficial. As metas projetadas para o ano são propostas.
        </p>
      </div>
    </aside>
  );
}
