import { notFound } from "next/navigation";
import { PainelView } from "@/components/PainelView";
import { getFiltros, getPainel } from "@/lib/api";

/** Busca painel + rotulos de tema e renderiza (compartilhado por [slug] e indicadores-globais). */
export async function PainelPage({ slug, q, base }: { slug: string; q: Record<string, string | undefined>; base: string }) {
  const [painel, filtros] = await Promise.all([
    getPainel(slug, { valor: q.valor, granularidade: q.granularidade, ano_inicio: q.ano_inicio, ano_fim: q.ano_fim }).catch(
      () => null,
    ),
    getFiltros(),
  ]);
  if (!painel) notFound();
  const rotulosTema: Record<string, string> = {
    ...Object.fromEntries(filtros.temas.map((t) => [t.codigo, t.label])),
    // despesa de natureza relevante ainda fora de ref/mapeamento_natureza_pls.csv
    nao_classificado: "Não classificado",
  };
  return <PainelView painel={painel} rotulosTema={rotulosTema} base={base} />;
}
