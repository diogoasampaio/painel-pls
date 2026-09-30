import Link from "next/link";
import {
  BadgePercent,
  Building2,
  ClipboardCheck,
  CupSoda,
  CloudFog,
  Droplets,
  FileCheck2,
  FileText,
  Fuel,
  GraduationCap,
  Handshake,
  HeartHandshake,
  Layers,
  Lightbulb,
  ListChecks,
  Package,
  Printer,
  Recycle,
  Share2,
  Sun,
  Wallet,
  Warehouse,
  Wheat,
  Wrench,
  Zap,
  type LucideIcon,
} from "lucide-react";
import { fmt, rotuloEixo, SITUACAO, EIXOS, type Ind, type SituacaoProjecao } from "@/lib/pls";
import { cn } from "@/lib/utils";

/** Ícone de cada indicador do núcleo (só em server components: ícone não atravessa para o cliente). */
export const ICONE_INDICADOR: Record<string, LucideIcon> = {
  N01: Zap, N02: Droplets, N03: CloudFog, N04: Recycle, N05: Building2, N06: Wrench, N07: Fuel, N08: Sun,
  N09: Package, N10: FileCheck2, N11: Share2, N12: Handshake, N13: GraduationCap, N14: Wallet, N15: ListChecks,
  // complementares
  N16: CupSoda, N17: FileText, N18: Printer, N19: Fuel, N20: Warehouse, N21: BadgePercent, N22: HeartHandshake, N23: Wheat,
};

export function complementar(i: { grupo?: string | null }) {
  return i.grupo === "complementar";
}

/** Selos do indicador: complementar e fora do índice sintético. */
export function SelosGrupo({ i }: { i: { grupo?: string | null; no_indice?: boolean | null } }) {
  if (!complementar(i) && i.no_indice !== false) return null;
  return (
    <span className="flex flex-wrap gap-1">
      {complementar(i) && (
        <span className="rounded-full border px-2 py-0.5 text-[0.7rem] font-medium text-muted-foreground">Complementar</span>
      )}
      {i.no_indice === false && (
        <span className="rounded-full border border-dashed px-2 py-0.5 text-[0.7rem] font-medium text-muted-foreground">
          Fora do índice
        </span>
      )}
    </span>
  );
}

export const ICONE_EIXO: Record<string, LucideIcon> = {
  "1": Zap, "2": Building2, "3": Recycle, "4": Lightbulb, "5": Handshake, "6": GraduationCap, transversal: ClipboardCheck,
};

/** Tom do medalhão por eixo: tokens de gráfico do DS/painel, sempre com o ícone em cor cheia sobre o tom claro. */
export const TOM_EIXO: Record<string, string> = {
  "1": "var(--chart-1)", "2": "var(--chart-8)", "3": "var(--chart-3)", "4": "var(--chart-7)", "5": "var(--chart-2)",
  "6": "var(--chart-4)", transversal: "var(--chart-5)",
};

export function Medalhao({ icone: Icone, tom, grande }: { icone: LucideIcon; tom: string; grande?: boolean }) {
  return (
    <span
      className={cn("flex shrink-0 items-center justify-center rounded-lg", grande ? "size-11" : "size-7")}
      style={{ background: `color-mix(in oklch, ${tom} 14%, transparent)`, color: tom }}
    >
      <Icone className={grande ? "size-5" : "size-4"} aria-hidden="true" />
    </span>
  );
}

/** Situação do ano corrente: pílula com texto (a cor nunca vai sozinha). */
export function SituacaoBadge({ situacao, className }: { situacao: SituacaoProjecao; className?: string }) {
  const s = SITUACAO[situacao];
  return (
    <span className={cn("inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold whitespace-nowrap", s.classe, className)}>
      {s.texto}
    </span>
  );
}

/** Barra empilhada com a contagem de indicadores por situação, e legenda com números. */
export function BarraSituacoes({ indicadores }: { indicadores: Ind[] }) {
  const cont = (Object.keys(SITUACAO) as SituacaoProjecao[])
    .map((s) => ({ s, n: indicadores.filter((i) => (i.projecao?.situacao_projecao ?? "sem_dado") === s).length }))
    .filter((x) => x.n > 0);
  const total = indicadores.length || 1;
  return (
    <div className="flex flex-col gap-3">
      <div className="flex h-3 w-full gap-0.5 overflow-hidden rounded-full" aria-hidden="true">
        {cont.map(({ s, n }) => (
          <span key={s} className={SITUACAO[s].barra} style={{ width: `${(100 * n) / total}%` }} />
        ))}
      </div>
      <ul className="m-0 flex list-none flex-wrap gap-x-4 gap-y-1 p-0 text-sm">
        {cont.map(({ s, n }) => (
          <li key={s} className="flex items-center gap-1.5">
            <span className={cn("size-2.5 rounded-full", SITUACAO[s].barra)} aria-hidden="true" />
            <span className="font-semibold tabular-nums">{n}</span> {SITUACAO[s].texto.toLowerCase()}
          </li>
        ))}
      </ul>
    </div>
  );
}

/** Pílulas de navegação (links): o estado fica na URL. O pill-group do DS é de botões e não serve para links. */
export function PilulasLink({
  rotulo,
  itens,
}: {
  rotulo: string;
  itens: { href: string; texto: string; ativo: boolean; icone?: LucideIcon; contagem?: number }[];
}) {
  return (
    <nav aria-label={rotulo} className="-mx-1 flex gap-2 overflow-x-auto px-1 pb-1 [scrollbar-width:thin] sm:flex-wrap sm:overflow-visible">
      {itens.map((i) => {
        const Icone = i.icone;
        return (
          <Link
            key={i.href}
            href={i.href}
            scroll={false}
            aria-current={i.ativo ? "page" : undefined}
            className={cn(
              "flex shrink-0 items-center gap-2 rounded-lg border px-3 py-2 text-sm font-medium no-underline outline-none transition-colors focus-visible:ring-3 focus-visible:ring-ring/50",
              i.ativo ? "border-primary bg-primary text-primary-foreground" : "bg-card text-foreground hover:bg-muted",
            )}
          >
            {Icone && <Icone className="size-4" aria-hidden="true" />}
            {i.texto}
            {i.contagem != null && (
              <span className={cn("text-xs tabular-nums", i.ativo ? "text-primary-foreground/80" : "text-muted-foreground")}>{i.contagem}</span>
            )}
          </Link>
        );
      })}
    </nav>
  );
}

/** Pílulas dos eixos com a contagem de indicadores, para as abas Eixos e Indicadores. */
export function PilulasEixos({ indicadores, atual, href }: { indicadores: Ind[]; atual: string; href: (eixo: string) => string }) {
  return (
    <PilulasLink
      rotulo="Eixos do PLS"
      itens={EIXOS.filter((e) => indicadores.some((i) => i.eixo_pls === e.codigo)).map((e) => ({
        href: href(e.codigo),
        texto: e.codigo === "transversal" ? e.curto : `${rotuloEixo(e.codigo)} · ${e.curto}`,
        ativo: e.codigo === atual,
        icone: ICONE_EIXO[e.codigo] ?? Layers,
        contagem: indicadores.filter((i) => i.eixo_pls === e.codigo).length,
      }))}
    />
  );
}

/** Valor da meta projetada na unidade do indicador (faixa: "29,74 a 40,23"). */
export function textoMeta(i: Ind): string {
  const p = i.projecao;
  if (!p || p.meta_projetada == null) return "—";
  if (p.regra === "faixa" && p.faixa_min != null && p.faixa_max != null) {
    return `${fmt(p.faixa_min, i.unidade)} a ${fmt(p.faixa_max, i.unidade)}`;
  }
  return `${p.sentido === "menor" ? "até " : p.sentido === "maior" ? "≥ " : ""}${fmt(p.meta_projetada, i.unidade)}`;
}
