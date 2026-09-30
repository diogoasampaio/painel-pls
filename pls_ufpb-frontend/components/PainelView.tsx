import { Controles } from "@/components/Controles";
import { Destaques } from "@/components/Destaques";
import { SerieChart } from "@/components/SerieChart";
import type { Painel } from "@/lib/api";
import { VALOR_LABEL } from "@/lib/format";

/**
 * Painéis de gasto sem sentido desejado: serviços continuados, capacitação e o
 * total da UFPB. Neles alta e queda ficam sem cor; nos demais (energia, água,
 * material, deslocamento) cair é o desejado.
 */
const GASTO_NEUTRO = new Set(["contratacoes", "visao-geral"]);

export function PainelView({ painel, rotulosTema, base }: { painel: Painel; rotulosTema: Record<string, string>; base: string }) {
  // por pessoa e por m²: valores pequenos, com centavos
  const perCapita = painel.valor === "per_capita" || painel.valor === "por_m2";
  const rotulos = painel.por === "tema_codigo" ? rotulosTema : undefined;
  return (
    <main className="container">
      <h1 className="page-title">{painel.label}</h1>
      <Controles base={base} valor={painel.valor} granularidade={painel.granularidade} />
      <Destaques
        itens={painel.destaques}
        rotulos={rotulos}
        perCapita={perCapita}
        polaridade={GASTO_NEUTRO.has(painel.slug) ? "neutro" : "menor"}
        valor={VALOR_LABEL[painel.valor]}
      />
      {painel.metricas.map((m) => {
        const pontos = painel.series.filter((s) => s.metrica === m.codigo);
        return (
          <section key={m.codigo} className="card">
            <h2 className="section-title">{m.label}</h2>
            {pontos.length ? (
              <SerieChart pontos={pontos} rotulos={rotulos} perCapita={perCapita} />
            ) : (
              <p className="caption">Sem dados carregados para esta métrica.</p>
            )}
          </section>
        );
      })}
      <p className="caption fonte">
        Fontes: Portal da Transparência (despesas e viagens), BCB/SGS (IPCA), contagem da comunidade acadêmica da UFPB (valores por pessoa).
        Despesa pelo valor pago, incluindo restos a pagar (a liquidação de restos a pagar não traz valor nos dados abertos). Emissões são estimativas.
      </p>
    </main>
  );
}
