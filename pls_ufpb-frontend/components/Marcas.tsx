import Link from "next/link";

/**
 * Marcas em public/marcas/ (ufpb-brasao.png, pls-ufpb.png, proplan.png). O brasao
 * usa a copia ufpb-brasao-168.png (3x a altura exibida; o original tem 263 KB).
 * <img> direto, e nao next/image: arquivo de public/ nao recebe o basePath
 * sozinho, entao o caminho leva /painel-pls (next.config.ts).
 */
const MARCAS = "/painel-pls/marcas";

/**
 * Cabecalho claro: o brasao e o logo do PLS sao coloridos (e o "PLS" e preto),
 * nao ficam legiveis sobre o azul. O filete de ouro no topo vem do brasao.
 */
export function Cabecalho() {
  return (
    <header className="border-b border-t-4 border-t-ufpb-ouro bg-card">
      <div className="mx-auto flex max-w-280 items-center gap-3 px-4 py-3">
        <Link href="/pls" className="flex min-w-0 items-center gap-3 text-foreground no-underline">
          <img src={`${MARCAS}/ufpb-brasao-168.png`} alt="Brasão da UFPB" className="h-14 w-auto shrink-0" />
          <span className="flex min-w-0 flex-col">
            <span className="text-base leading-tight font-semibold text-primary">Painel de Sustentabilidade</span>
            <span className="truncate text-xs text-muted-foreground">Universidade Federal da Paraíba</span>
          </span>
        </Link>
        <img src={`${MARCAS}/pls-ufpb.png`} alt="PLS UFPB – Plano de Logística Sustentável" className="ml-auto h-10 w-auto shrink-0 sm:h-14" />
      </div>
    </header>
  );
}

/** Rodape com a autoria do painel: PROPLAN/UFPB. */
export function Rodape() {
  return (
    <footer className="mt-12 border-t bg-card">
      <div className="mx-auto flex max-w-280 flex-wrap items-center gap-3 px-4 py-6 text-sm text-muted-foreground">
        <img src={`${MARCAS}/proplan.png`} alt="PROPLAN" className="h-10 w-auto shrink-0" />
        <p className="m-0">
          Desenvolvido pela <span className="font-semibold text-foreground">Pró-Reitoria de Planejamento e Desenvolvimento (PROPLAN)</span>{" "}
          da Universidade Federal da Paraíba.
        </p>
      </div>
    </footer>
  );
}
