import type { Execucao } from "@/lib/api";

/** Indicador do núcleo como vem de /pls/execucao?conjunto=nucleo. */
export type Ind = Execucao["indicadores"][number];
export type Projecao = NonNullable<Ind["projecao"]>;
export type SituacaoProjecao = Projecao["situacao_projecao"];

/** Eixos do PLS UFPB 2025–2029 na ordem do plano; "transversal" = gestão do plano (N15). */
export const EIXOS: { codigo: string; nome: string; curto: string }[] = [
  { codigo: "1", nome: "Racionalização e consumo consciente", curto: "Consumo" },
  { codigo: "2", nome: "Ocupação dos espaços físicos", curto: "Espaços" },
  { codigo: "3", nome: "Objetos de menor impacto ambiental", curto: "Menor impacto" },
  { codigo: "4", nome: "Inovação no mercado", curto: "Inovação" },
  { codigo: "5", nome: "Negócios de impacto", curto: "Negócios de impacto" },
  { codigo: "6", nome: "Divulgação e capacitação", curto: "Capacitação" },
  { codigo: "transversal", nome: "Gestão do plano", curto: "Gestão do plano" },
];

export function nomeEixo(codigo: string) {
  return EIXOS.find((e) => e.codigo === codigo)?.nome ?? `Eixo ${codigo}`;
}

export function rotuloEixo(codigo: string) {
  return codigo === "transversal" ? "Transversal" : `Eixo ${codigo}`;
}

/** Situação da execução do ano corrente contra a meta projetada. Cor só por token do DS. */
export const SITUACAO: Record<SituacaoProjecao, { texto: string; classe: string; barra: string; ordem: number }> = {
  no_rumo: { texto: "No rumo", classe: "bg-success text-success-foreground", barra: "bg-success", ordem: 0 },
  atencao: { texto: "Atenção", classe: "bg-warning text-warning-foreground", barra: "bg-warning", ordem: 1 },
  fora_do_rumo: { texto: "Fora do rumo", classe: "bg-destructive text-white", barra: "bg-destructive", ordem: 2 },
  sem_dado: { texto: "Sem dado", classe: "bg-muted text-muted-foreground", barra: "bg-muted-foreground/40", ordem: 3 },
};

const MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"];
export const MESES_LONGOS = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"];

const n0 = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 0 });
const n1 = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 1 });
const n2 = new Intl.NumberFormat("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const compacto = new Intl.NumberFormat("pt-BR", { notation: "compact", maximumFractionDigits: 1 });

/** Número na unidade do indicador: "66,7%", "R$ 105,22/m²", "1.407 tCO₂e", "R$ 635,4 mil". */
export function fmt(valor: number | null | undefined, unidade: string, curto = false): string {
  if (valor == null || !Number.isFinite(valor)) return "—";
  if (unidade === "%") return `${n1.format(valor)}%`;
  if (unidade === "R$") return curto || Math.abs(valor) >= 1e5 ? `R$ ${compacto.format(valor)}` : `R$ ${n0.format(valor)}`;
  if (unidade.startsWith("R$/")) return `R$ ${n2.format(valor)}/${unidade.slice(3)}`;
  const casas = Math.abs(valor) >= 100 ? n0 : Math.abs(valor) >= 10 ? n1 : n2;
  const numero = curto && Math.abs(valor) >= 1e4 ? compacto.format(valor) : casas.format(valor);
  return `${numero} ${unidade}`;
}

/** Série anual com ano completo e valor. */
export function completos(i: Ind) {
  return (i.historico ?? []).filter((h) => h.ano_completo && h.valor != null) as { ano: number; valor: number }[];
}

/**
 * Variação do último ano completo sobre o anterior. Em %, a variação é em
 * pontos percentuais. `bom` segue a polaridade (neutro = null, sem cor).
 */
export function variacao(i: Ind): { texto: string; bom: boolean | null; ano: number } | null {
  const c = completos(i);
  const [ant, ult] = [c.at(-2), c.at(-1)];
  if (!ant || !ult) return null;
  const pp = i.unidade === "%";
  const delta = pp ? ult.valor - ant.valor : ant.valor ? ((ult.valor - ant.valor) / Math.abs(ant.valor)) * 100 : NaN;
  if (!Number.isFinite(delta)) return null;
  if (Math.abs(delta) < 0.05) return { texto: "estável", bom: null, ano: ant.ano };
  const queda = delta < 0;
  const bom = i.polaridade === "menor" ? queda : i.polaridade === "maior" ? !queda : null;
  return { texto: `${queda ? "↓" : "↑"} ${n1.format(Math.abs(delta))}${pp ? " p.p." : "%"}`, bom, ano: ant.ano };
}

/** "jan–jul" para os meses com dado do ano corrente. */
export function periodo(meses: number | null | undefined) {
  if (!meses) return null;
  return meses >= 12 ? "ano completo" : meses === 1 ? "jan" : `jan–${MESES[meses - 1]}`;
}

/** Como a projeção do ano foi feita, em uma frase. */
export function comoProjetou(p: Projecao): string {
  const ate = periodo(p.meses);
  switch (p.metodo) {
    case "mesmo_periodo":
      return `Ano anterior completo ajustado pela variação de ${ate} sobre o mesmo período do ano anterior.`;
    case "anualizado":
      return `Acumulado de ${ate} levado a 12 meses (sem ano anterior completo para comparar).`;
    case "acumulado":
      return `Percentual acumulado de ${ate}: a proporção do ano até agora é a estimativa do ano.`;
    case "fotografia":
      return "Posição do plano de ações na data de referência do acompanhamento.";
    case "ano_completo":
      return "Ano completo: valor apurado.";
    default:
      return "Sem dado do ano corrente para projetar.";
  }
}

/** Regra da meta projetada, em uma frase curta. */
export function regraMeta(p: Projecao, unidade: string): string {
  const par = p.parametro != null ? String(p.parametro).replace(".", ",") : "";
  switch (p.regra) {
    case "reducao_anual":
      return `−${par}% ao ano sobre ${p.ano_base}`;
    case "reducao_vs_base":
      return `−${par}% sobre ${p.ano_base}`;
    case "minimo":
      return `mínimo de ${fmt(p.parametro, unidade)}`;
    case "manter":
      return `manter o ${p.ano_base?.includes("-") ? `nível médio de ${p.ano_base.replace("-", "–")}` : `nível de ${p.ano_base}`}`;
    case "faixa":
      return `até ${par}% da média de ${p.ano_base?.replace("-", "–")}`;
    default:
      return "";
  }
}

/**
 * Dados de origem de cada indicador (aba Indicadores): gráficos montados com
 * séries dos painéis temáticos, filtradas nos subtemas que compõem o
 * indicador. O painel de compras e contratações, por exemplo, traz todos os
 * serviços; o N06 usa só "Manutenção predial". Indicador sem entrada aqui
 * vem de fonte que não está em painel temático (PNCP, cadastro de CNPJ, EVG).
 */
export type ParteGrafico = { slug: string; metrica: string; subtemas?: string[] };
export type GraficoAssociado = { titulo: string; partes: ParteGrafico[] };

export const DADOS_ASSOCIADOS: Record<string, { texto: string; graficos: GraficoAssociado[] }> = {
  N01: {
    texto: "Numerador do indicador (kWh medido nas faturas da Energisa, por campus) e o gasto com as faturas.",
    graficos: [
      { titulo: "Consumo de energia por campus (kWh)", partes: [{ slug: "energia", metrica: "consumo_kwh" }] },
      { titulo: "Pago nas faturas de energia elétrica (R$)", partes: [{ slug: "energia", metrica: "pago", subtemas: ["Fatura de energia elétrica"] }] },
    ],
  },
  N02: {
    texto: "Numerador do indicador (m³ medido nas faturas da CAGEPA, por campus) e o gasto com as faturas.",
    graficos: [
      { titulo: "Consumo de água por campus (m³)", partes: [{ slug: "agua", metrica: "consumo_m3" }] },
      { titulo: "Pago nas faturas de água e esgoto (R$)", partes: [{ slug: "agua", metrica: "pago", subtemas: ["Fatura de água e esgoto"] }] },
    ],
  },
  N03: {
    texto: "As bases das emissões: combustível da frota (escopo 1), energia da rede (escopo 2) e viagens aéreas (escopo 3).",
    graficos: [
      { titulo: "Escopo 1: combustível abastecido pela frota (L)", partes: [{ slug: "deslocamento", metrica: "consumo_litros" }] },
      { titulo: "Escopo 2: energia consumida da rede (kWh)", partes: [{ slug: "energia", metrica: "consumo_kwh" }] },
      { titulo: "Escopo 3: emissões das viagens aéreas (kg CO₂e)", partes: [{ slug: "deslocamento", metrica: "co2e_kg" }] },
    ],
  },
  N04: {
    texto: "O peso destinado vem dos relatórios de fiscalização; aqui, o valor empenhado nos serviços de coleta e destinação.",
    graficos: [{ titulo: "Empenhado em coleta e destinação de resíduos (R$)", partes: [{ slug: "contratacoes", metrica: "empenhado_itens", subtemas: ["Coleta e destinação de resíduos"] }] }],
  },
  N05: {
    texto: "Os quatro componentes do custo de funcionamento: energia, água, limpeza e manutenção predial.",
    graficos: [
      {
        titulo: "Pago nos componentes do custo de funcionamento (R$)",
        partes: [
          { slug: "energia", metrica: "pago", subtemas: ["Fatura de energia elétrica"] },
          { slug: "agua", metrica: "pago", subtemas: ["Fatura de água e esgoto"] },
          { slug: "contratacoes", metrica: "pago", subtemas: ["Limpeza e conservação", "Manutenção predial"] },
        ],
      },
    ],
  },
  N06: {
    texto: "Numerador do indicador: o pago em manutenção predial.",
    graficos: [{ titulo: "Pago em manutenção predial (R$)", partes: [{ slug: "contratacoes", metrica: "pago", subtemas: ["Manutenção predial"] }] }],
  },
  N07: {
    texto: "Litros abastecidos pela frota por combustível: etanol e diesel S10 formam o numerador; todos, o denominador.",
    graficos: [{ titulo: "Combustível abastecido pela frota (L)", partes: [{ slug: "deslocamento", metrica: "consumo_litros" }] }],
  },
  N09: {
    texto: "Itens de material de consumo empenhados com atributo sustentável e o gasto com material de consumo.",
    graficos: [
      { titulo: "Itens com atributo sustentável empenhados (R$)", partes: [{ slug: "contratacoes", metrica: "empenhado_itens", subtemas: ["Item com atributo sustentável"] }] },
      { titulo: "Pago em material de consumo (R$)", partes: [{ slug: "material-consumo", metrica: "pago" }] },
    ],
  },
  N16: {
    texto: "Valor empenhado em copos descartáveis (a quantidade sai desse valor dividido pelo preço da compra no PNCP).",
    graficos: [{ titulo: "Empenhado em copos descartáveis (R$)", partes: [{ slug: "material-consumo", metrica: "empenhado_itens", subtemas: ["Copos descartáveis"] }] }],
  },
  N17: {
    texto: "Papel empenhado como material e o pago ao Almoxarifado Virtual Nacional, de onde veio a maior parte do papel até 2025.",
    graficos: [
      { titulo: "Empenhado em papel A4 (R$)", partes: [{ slug: "material-consumo", metrica: "empenhado_itens", subtemas: ["Papel A4 / resmas"] }] },
      { titulo: "Pago ao Almoxarifado Virtual Nacional (R$)", partes: [{ slug: "material-consumo", metrica: "pago", subtemas: ["Almoxarifado Virtual Nacional (AVN)"] }] },
    ],
  },
  N18: {
    texto: "Valor empenhado em toner e cartuchos.",
    graficos: [{ titulo: "Empenhado em toner e cartuchos (R$)", partes: [{ slug: "material-consumo", metrica: "empenhado_itens", subtemas: ["Toner e cartuchos"] }] }],
  },
  N19: {
    texto: "Litros abastecidos pela frota por combustível: gasolina e diesel formam o indicador.",
    graficos: [{ titulo: "Combustível abastecido pela frota (L)", partes: [{ slug: "deslocamento", metrica: "consumo_litros" }] }],
  },
  N20: {
    texto: "Pagamentos ao operador do Almoxarifado Virtual Nacional: a adesão é medida pelas UGs que pagaram no ano.",
    graficos: [{ titulo: "Pago ao Almoxarifado Virtual Nacional (R$)", partes: [{ slug: "material-consumo", metrica: "pago", subtemas: ["Almoxarifado Virtual Nacional (AVN)"] }] }],
  },
  N14: {
    texto: "Pago na ação 4572 (o indicador) e, para contexto, treinamento pago por outras ações.",
    graficos: [
      { titulo: "Pago em treinamento (R$)", partes: [{ slug: "contratacoes", metrica: "pago", subtemas: ["Serviços de treinamento (ação 4572)", "Treinamento (outras ações)"] }] },
    ],
  },
};

/** Fonte de cada indicador sem gráfico associado, para a nota da aba Indicadores. */
export const SEM_PAINEL: Record<string, string> = {
  N08: "A geração das usinas solares ainda depende da informação do setor responsável.",
  N10: "Os editais e termos de referência vêm do PNCP e são lidos um a um; a contagem por critério está no catálogo de metas.",
  N11: "As compras compartilhadas vêm do PNCP e do Compras.gov.br (IRP, participantes e adesões).",
  N12: "O porte e a sede dos fornecedores vêm do cadastro aberto de CNPJ da Receita, cruzado com os pagamentos.",
  N13: "As certificações vêm dos arquivos da Escola Virtual de Governo (ENAP), sem dados pessoais.",
  N15: "O cumprimento das ações vem do acompanhamento semestral dos responsáveis, com evidência.",
  N21: "O campo de margem de preferência vem dos itens das contratações publicadas no PNCP.",
  N22: "Os editais e termos de referência de mão de obra exclusiva vêm do PNCP e são lidos um a um.",
  N23: "Os editais e termos de referência de gêneros alimentícios vêm do PNCP e são lidos um a um.",
};
