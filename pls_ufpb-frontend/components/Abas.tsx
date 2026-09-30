"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { BarChart3, Layers, Target, TrendingUp, type LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

const ABAS: { href: string; texto: string; icone: LucideIcon; ativa: (p: string) => boolean }[] = [
  { href: "/pls", texto: "Visão geral", icone: BarChart3, ativa: (p) => p === "/pls" || p === "/" },
  { href: "/pls/eixos", texto: "Eixos do PLS", icone: Layers, ativa: (p) => p.startsWith("/pls/eixos") },
  { href: "/pls/indicadores", texto: "Indicadores", icone: TrendingUp, ativa: (p) => p === "/pls/indicadores" },
];

/**
 * Abas principais do painel, logo abaixo do cabeçalho. A aba ativa é a
 * pílula preenchida com a cor primária; o link leva aria-current="page".
 * No celular a faixa rola na horizontal em vez de quebrar.
 */
export function Abas() {
  const caminho = usePathname() ?? "/pls";
  return (
    <nav aria-label="Seções do painel" className="sticky top-0 z-30 border-b bg-card/95 backdrop-blur supports-[backdrop-filter]:bg-card/80">
      <div className="mx-auto flex max-w-280 items-center gap-1 overflow-x-auto px-4 py-2 [scrollbar-width:none]">
        {ABAS.map((a) => {
          const ativa = a.ativa(caminho);
          const Icone = a.icone;
          return (
            <Link
              key={a.href}
              href={a.href}
              aria-current={ativa ? "page" : undefined}
              className={cn(
                "flex shrink-0 items-center gap-2 rounded-lg px-3.5 py-2 text-sm font-medium no-underline outline-none transition-colors focus-visible:ring-3 focus-visible:ring-ring/50",
                ativa ? "bg-primary text-primary-foreground shadow-xs" : "text-foreground hover:bg-muted",
              )}
            >
              <Icone className="size-4" aria-hidden="true" />
              {a.texto}
            </Link>
          );
        })}
        <Link
          href="/pls/metas"
          aria-current={caminho.startsWith("/pls/metas") ? "page" : undefined}
          className={cn(
            "ml-auto flex shrink-0 items-center gap-2 rounded-lg px-3.5 py-2 text-sm font-medium no-underline outline-none transition-colors hover:bg-muted focus-visible:ring-3 focus-visible:ring-ring/50",
            caminho.startsWith("/pls/metas") ? "text-primary" : "text-muted-foreground",
          )}
        >
          <Target className="size-4" aria-hidden="true" />
          Catálogo de metas
        </Link>
      </div>
    </nav>
  );
}
