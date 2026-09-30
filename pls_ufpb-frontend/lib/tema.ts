/**
 * Tema de cores do LEMA-DS, escolhido por projeto em TEMA_DS (.env.local ou
 * variável do serviço): ufpb (padrão, cores do brasão), neutro, blue, green ou violet. O tema troca primary,
 * secondary, accent e ring (classes em app/globals.css); success, warning,
 * risk-* e as cores de gráfico não mudam. Valor desconhecido cai no padrão.
 */
export const TEMAS = ["ufpb", "neutro", "blue", "green", "violet"] as const;
export type Tema = (typeof TEMAS)[number];

const PADRAO: Tema = "ufpb";

export function temaDoProjeto(): Tema {
  const t = (process.env.TEMA_DS ?? "").trim().toLowerCase();
  return (TEMAS as readonly string[]).includes(t) ? (t as Tema) : PADRAO;
}

/** Classe do <html>: o neutro é a base do DS, sem classe. */
export function classeDoTema(tema: Tema = temaDoProjeto()): string | undefined {
  return tema === "neutro" ? undefined : tema;
}
