const API_BASE_URL = process.env.API_BASE_URL ?? "http://127.0.0.1:8001";

export type PainelResumo = { slug: string; label: string };

export type Filtros = {
  anos: number[];
  temas: { codigo: string; label: string; eixo: string | null }[];
  metricas: string[];
};

export type PontoSerie = {
  periodo: string;
  metrica: string;
  grupo: string | null;
  valor: number | null;
  unidade: string | null;
};

export type Destaque = {
  grupo: string | null;
  ano: number;
  valor: number;
  ano_anterior: number | null;
  valor_anterior: number | null;
  variacao_pct: number | null;
};

export type Valor = "nominal" | "real" | "per_capita" | "por_m2";
export type Granularidade = "ano" | "mes";

export type Painel = {
  slug: string;
  label: string;
  metricas: { codigo: string; label: string }[];
  valor: Valor;
  granularidade: Granularidade;
  por: "tema_codigo" | "subtema";
  series: PontoSerie[];
  destaques: Destaque[];
};

/**
 * So chamar a partir de server components / route handlers. A FastAPI
 * ouve apenas em 127.0.0.1 e nao deve ser alcancada pelo navegador.
 */
async function apiFetch<T>(path: string, params?: Record<string, string | undefined>): Promise<T> {
  const url = new URL(path, API_BASE_URL);
  for (const [key, value] of Object.entries(params ?? {})) {
    if (value) url.searchParams.set(key, value);
  }
  const res = await fetch(url, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`API ${path} respondeu ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export function getPaineis() {
  return apiFetch<PainelResumo[]>("/pls/paineis");
}

export function getFiltros() {
  return apiFetch<Filtros>("/pls/filtros");
}

export function getPainel(slug: string, params: { valor?: string; granularidade?: string; ano_inicio?: string; ano_fim?: string }) {
  return apiFetch<Painel>(`/pls/${encodeURIComponent(slug)}`, params);
}

export type ValorMeta = {
  ano: number;
  valor: number | null;
  /** R$ como foi pago (sem correcao), quando `valor` esta corrigido pelo IPCA de `ref_ipca` */
  valor_nominal?: number | null;
  ref_ipca?: string | null;
  origem: string;
  fonte: string | null;
  ano_completo: boolean;
  ano_referencia: number | null;
  variacao_pct: number | null;
  situacao: "atingida" | "nao_atingida" | "em_andamento" | "linha_de_base" | "historico" | "acompanhamento";
  /** grau de alcance da meta no ano (0-100) */
  alcance_pct?: number | null;
  faixa?: string | null;
};

export type IndicadorMeta = {
  id: string;
  eixo_pls: string;
  tabela_pls: string | null;
  objetivo: string;
  indicador: string;
  formula: string;
  unidade: string;
  meta: string;
  tipo_meta: string;
  meta_valor: number | null;
  ano_base: number | null;
  responsavel: string;
  automacao: "automatico" | "integracao" | "informado";
  tipo_fonte: "publica" | "fornecedor" | "interna" | "documental";
  rota_automacao: string;
  /** questoes em aberto para a Comissao do PLS (ref/decisoes_comissao.csv) */
  decisoes?: Decisao[];
  valores: ValorMeta[];
};

export type Decisao = {
  id: string;
  questao: string;
  contexto: string | null;
  opcoes: string | null;
  efeito: string | null;
  situacao: "pendente" | "decidida";
  decisao: string | null;
};

export type Metas = {
  eixos: { eixo_pls: string; eixo: string; descricao: string }[];
  indicadores: IndicadorMeta[];
};

export function getMetas(params: { eixo?: string }) {
  return apiFetch<Metas>("/pls/metas", params);
}

export type NivelSaude = "erro" | "atencao" | "info" | "ok";

export type Saude = {
  execucao: string | null;
  itens: {
    verificacao: string;
    modulo: string;
    nivel: NivelSaude;
    titulo: string;
    quantidade: number;
    detalhe: string[];
    acao_sugerida: string;
  }[];
  historico: { execucao: string; erro: number; atencao: number }[];
};

export function getSaude() {
  return apiFetch<Saude>("/pls/saude");
}

/**
 * Proxy dos formularios (route handlers em app/api/formularios): repassa o
 * token do setor e o corpo para a FastAPI, que continua fora do alcance do
 * navegador. So estes caminhos passam.
 */
export async function proxyFormulario(caminho: "acesso" | "acompanhamento" | "valores", req: Request): Promise<Response> {
  const token = req.headers.get("x-token-formulario") ?? "";
  const init: RequestInit = { method: req.method, headers: { "X-Token-Formulario": token }, cache: "no-store" };
  if (req.method === "POST") {
    const corpo = await req.text();
    if (corpo.length > 20_000) return Response.json({ detail: "Envio grande demais" }, { status: 413 });
    init.body = corpo;
    (init.headers as Record<string, string>)["Content-Type"] = "application/json";
  }
  try {
    const res = await fetch(new URL(`/pls/formularios/${caminho}`, API_BASE_URL), init);
    return new Response(await res.text(), { status: res.status, headers: { "Content-Type": "application/json" } });
  } catch {
    return Response.json({ detail: "API indisponível" }, { status: 502 });
  }
}

export type FaixaCodigo = "atingida" | "proxima" | "progresso" | "distante" | "nao_avaliavel" | "sem_dado" | "sem_meta";

export type Execucao = {
  conjunto: "plano" | "nucleo";
  ano: number | null;
  /** ano dos eixos e indicadores: o ultimo com metas avaliadas */
  ano_detalhe: number | null;
  serie: {
    ano: number;
    indice_sintetico: number | null;
    indice_metas: number | null;
    indice_metas_usado: number | null;
    ano_metas: number | null;
    indice_acoes: number | null;
    componentes: string;
    n_indicadores: number;
    n_com_meta: number;
    n_avaliados: number;
    cobertura_pct: number | null;
    ano_fechado: boolean;
    faixas: Record<FaixaCodigo, number>;
  }[];
  eixos: {
    eixo_pls: string;
    eixo: string | null;
    indice_metas: number | null;
    n_com_meta: number;
    n_avaliados: number;
    cobertura_pct: number | null;
    faixas: Record<FaixaCodigo, number>;
  }[];
  indicadores: {
    codigo: string;
    indicador_id: string | null;
    indicador: string;
    eixo_pls: string;
    tipo_meta: string;
    alcance_pct: number | null;
    faixa: FaixaCodigo;
    situacao: string | null;
    valor: number | null;
    unidade: string;
    meta: string | null;
    meta_sugerida?: string | null;
    formula?: string | null;
    automacao?: string | null;
    fonte?: string | null;
    ultimo: { ano: number; valor: number; ano_completo: boolean | null } | null;
    /** so no nucleo: sentido desejado (ref/fichas_nucleo.csv); neutro = depende do contexto */
    polaridade?: "menor" | "maior" | "neutro" | null;
    /** so no nucleo: serie anual desde o 1o ano com dado */
    historico?: { ano: number; valor: number | null; ano_completo: boolean | null }[];
    /** so no nucleo: o que mede, periodicidade e responsavel (ref/fichas_nucleo.csv) */
    o_que_mede?: string | null;
    periodicidade?: string | null;
    responsavel?: string | null;
    /** so no nucleo: meta projetada e projecao do ano corrente (proposta a validar; ETL execucao/projecao.py) */
    /** so no nucleo: "nucleo" (N01-N15) ou "complementar" (N16 em diante) */
    grupo?: "nucleo" | "complementar" | null;
    /** so no nucleo: false = aparece no painel, mas fica fora do indice sintetico */
    no_indice?: boolean | null;
    /** so no nucleo: questoes em aberto para a Comissao do PLS */
    decisoes?: Decisao[];
    projecao?: {
      ano: number;
      valor_parcial: number | null;
      /** ultimo mes do ano com dado (null na fotografia do N15) */
      meses: number | null;
      projecao: number | null;
      metodo: "mesmo_periodo" | "anualizado" | "acumulado" | "fotografia" | "ano_completo" | "sem_dado";
      meta_projetada: number | null;
      faixa_min: number | null;
      faixa_max: number | null;
      regra: "reducao_anual" | "reducao_vs_base" | "minimo" | "manter" | "faixa";
      parametro: number | null;
      ano_base: string | null;
      sentido: "menor" | "maior" | "faixa";
      fundamento: string | null;
      situacao_projecao: "no_rumo" | "atencao" | "fora_do_rumo" | "sem_dado";
      alcance_projecao: number | null;
    } | null;
  }[];
  faixas: { codigo: FaixaCodigo; faixa: string; alcance_minimo: number | null; descricao: string }[];
  parametros: { peso_metas: number; peso_acoes: number; agregacao_metas: string; primeiro_ano: number };
};

export function getExecucao(params: { conjunto?: string; ano?: string }) {
  return apiFetch<Execucao>("/pls/execucao", params);
}
