import type { FaixaCodigo } from "@/lib/api";

/**
 * Faixas de execucao -> tokens do LEMA-DS (nunca cor crua). Escala de risco do
 * DS: risk-1 (maior) ... risk-4 (menor); atingida usa success. As faixas sem
 * alcance numerico ficam neutras. Texto sobre risk-3/risk-4 (amarelo e lima) usa
 * warning-foreground, que e escuro nos dois temas.
 */
export const FAIXA_COR: Record<FaixaCodigo, string> = {
  atingida: "bg-success text-success-foreground",
  proxima: "bg-risk-4 text-warning-foreground",
  progresso: "bg-risk-3 text-warning-foreground",
  distante: "bg-risk-1 text-success-foreground",
  nao_avaliavel: "bg-secondary text-secondary-foreground",
  sem_dado: "bg-muted-foreground text-background",
  sem_meta: "bg-muted text-muted-foreground",
};
