import { ChevronDown } from "lucide-react";

const MARCAS = "/painel-pls/marcas";

/** Rede de pontos (como a do SAEGO): dados conectados sobre a paisagem. Posições fixas, sem aleatório no render. */
const NOS: [number, number][] = [
  [70, 120], [180, 70], [260, 190], [120, 300], [330, 110], [1120, 90], [1240, 170], [1360, 80], [1300, 290],
  [1180, 330], [1010, 200], [420, 330], [1400, 380], [40, 420], [1080, 420],
];
const ARESTAS: [number, number][] = [
  [0, 1], [1, 2], [0, 3], [2, 4], [1, 4], [2, 3], [5, 6], [6, 7], [6, 8], [8, 9], [5, 10], [9, 10], [3, 11], [8, 12], [3, 13], [9, 14],
];

/** Folha: contorno + nervura central. */
function Folha({ x, y, escala, giro, className }: { x: number; y: number; escala: number; giro: number; className?: string }) {
  return (
    <g transform={`translate(${x} ${y}) rotate(${giro}) scale(${escala})`} className={className}>
      <path d="M0 0 C 50 -70 150 -70 200 0 C 150 70 50 70 0 0 Z" fill="white" fillOpacity="0.07" stroke="white" strokeOpacity="0.16" strokeWidth="1.5" vectorEffect="non-scaling-stroke" />
      <path d="M0 0 L 200 0 M60 0 L 95 -28 M100 0 L 135 -26 M60 0 L 95 28 M100 0 L 135 26" stroke="white" strokeOpacity="0.14" strokeWidth="1.2" fill="none" vectorEffect="non-scaling-stroke" />
    </g>
  );
}

function Paisagem() {
  return (
    <svg className="absolute inset-0 h-full w-full" viewBox="0 0 1440 560" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
      <defs>
        <radialGradient id="hero-sol" cx="0.5" cy="0.5" r="0.5">
          <stop offset="0" stopColor="var(--hero-sol)" stopOpacity="0.55" />
          <stop offset="1" stopColor="var(--hero-sol)" stopOpacity="0" />
        </radialGradient>
        <linearGradient id="hero-colina" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="white" stopOpacity="0.10" />
          <stop offset="1" stopColor="white" stopOpacity="0.02" />
        </linearGradient>
      </defs>
      {/* sol e anéis: energia renovável */}
      <circle cx="1180" cy="130" r="260" fill="url(#hero-sol)" />
      {[70, 120, 175].map((r) => (
        <circle key={r} cx="1180" cy="130" r={r} fill="none" stroke="white" strokeOpacity="0.1" strokeWidth="1" />
      ))}
      {/* rede de dados */}
      <g stroke="white" strokeOpacity="0.22" strokeWidth="1">
        {ARESTAS.map(([a, b]) => (
          <line key={`${a}-${b}`} x1={NOS[a][0]} y1={NOS[a][1]} x2={NOS[b][0]} y2={NOS[b][1]} />
        ))}
      </g>
      {NOS.map(([x, y], k) => (
        <circle key={k} cx={x} cy={y} r={k % 3 === 0 ? 4.5 : 3} fill="white" fillOpacity={k % 3 === 0 ? 0.75 : 0.45} />
      ))}
      {/* folhas */}
      <Folha x={-30} y={520} escala={1.6} giro={-38} className="hero-folha" />
      <Folha x={150} y={560} escala={1.1} giro={-70} className="hero-folha hero-folha-2" />
      <Folha x={1290} y={560} escala={1.4} giro={-140} className="hero-folha hero-folha-2" />
      <Folha x={1440} y={470} escala={0.9} giro={-165} className="hero-folha" />
      {/* colinas */}
      <path d="M0 470 C 240 420 420 500 720 460 C 1000 425 1200 500 1440 450 L1440 560 L0 560 Z" fill="url(#hero-colina)" />
      <path d="M0 515 C 300 480 560 540 860 505 C 1100 480 1280 530 1440 505 L1440 560 L0 560 Z" fill="white" fillOpacity="0.05" />
    </svg>
  );
}

/**
 * Hero da Visão geral: cena em tela cheia (gradiente verde-azulado da UFPB,
 * sol, folhas, rede de dados e colinas), com a identidade do PLS ao centro e
 * os números-síntese em pílulas. Cores em tokens --hero-* (app/globals.css);
 * a cena é escura nos dois temas, então o texto é sempre claro.
 */
export function HeroSustentabilidade({
  indicadores,
  complementares = 0,
  indice,
  anoIndice,
  anos,
}: {
  indicadores: number;
  complementares?: number;
  indice: number | null;
  anoIndice: number | null;
  anos: [number, number] | null;
}) {
  const pct = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 1 });
  return (
    <section aria-labelledby="hero-titulo" className="hero-sust relative isolate overflow-hidden text-white">
      <Paisagem />
      <div className="relative mx-auto flex max-w-280 flex-col items-center gap-5 px-4 pt-14 pb-20 text-center sm:pt-20 sm:pb-24">
        <span className="flex h-24 items-center justify-center rounded-2xl bg-white px-5 py-3 shadow-lg ring-4 ring-white/15">
          <img src={`${MARCAS}/pls-ufpb.png`} alt="" className="h-full w-auto object-contain" />
        </span>
        <p className="m-0 rounded-full bg-white/12 px-4 py-1.5 text-xs font-semibold tracking-[0.2em] uppercase ring-1 ring-white/20 backdrop-blur-sm">
          PLS UFPB · 2025–2029
        </p>
        <h1 id="hero-titulo" className="m-0 max-w-4xl text-4xl leading-[1.05] font-bold tracking-tight text-balance sm:text-5xl lg:text-6xl">
          Painel de <span className="text-[var(--hero-destaque)]">Sustentabilidade</span> da UFPB
        </h1>
        <p className="m-0 max-w-2xl text-base text-pretty text-white/85 sm:text-lg">
          Acompanhe a execução do Plano de Logística Sustentável pelos {indicadores} indicadores do núcleo: energia, água,
          emissões, compras sustentáveis, negócios de impacto e capacitação, com metas e evolução ano a ano.
        </p>
        <ul className="m-0 flex list-none flex-wrap justify-center gap-2 p-0 pt-1">
          <li className="rounded-full bg-white/10 px-4 py-1.5 text-sm font-medium ring-1 ring-white/25">
            {indicadores} indicadores do núcleo{complementares ? ` + ${complementares} complementares` : ""}
          </li>
          <li className="rounded-full bg-white/10 px-4 py-1.5 text-sm font-medium ring-1 ring-white/25">6 eixos + gestão do plano</li>
          {indice != null && (
            <li className="rounded-full bg-white/10 px-4 py-1.5 text-sm font-medium ring-1 ring-white/25">
              Índice sintético {pct.format(indice)}% ({anoIndice})
            </li>
          )}
        </ul>
        {anos && (
          <p className="m-0 text-sm text-white/70">
            Dados de {anos[0]} a {anos[1]} · atualização mensal a partir de dados públicos e dos setores
          </p>
        )}
      </div>
      <a
        href="#panorama"
        aria-label="Ir para o panorama"
        className="absolute bottom-4 left-1/2 flex size-9 -translate-x-1/2 items-center justify-center rounded-full text-white/80 no-underline outline-none hover:text-white focus-visible:ring-3 focus-visible:ring-white/60"
      >
        <ChevronDown className="size-6 motion-safe:animate-bounce" aria-hidden="true" />
      </a>
    </section>
  );
}
