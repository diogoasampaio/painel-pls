const brl = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 });
const brlCentavos = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL", minimumFractionDigits: 2 });
const num = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 1 });
const compacto = new Intl.NumberFormat("pt-BR", { notation: "compact", maximumFractionDigits: 1 });

/** Valor com unidade. Per capita em R$ fica com centavos (valores pequenos). */
export function formatValor(valor: number | null, unidade: string | null, perCapita = false): string {
  if (valor == null) return "—";
  if (unidade === "R$") return perCapita ? brlCentavos.format(valor) : brl.format(valor);
  if (unidade === "kg CO2e" && Math.abs(valor) >= 1000) return `${num.format(valor / 1000)} t CO2e`;
  return `${num.format(valor)}${unidade && unidade !== "un" ? ` ${unidade}` : ""}`;
}

export function formatEixo(valor: number, unidade: string | null): string {
  return unidade === "R$" ? `R$ ${compacto.format(valor)}` : compacto.format(valor);
}

export const VALOR_LABEL: Record<string, string> = {
  real: "R$ constantes (IPCA)",
  nominal: "R$ correntes",
  per_capita: "Por pessoa da comunidade acadêmica",
  por_m2: "Por m² construído",
};
