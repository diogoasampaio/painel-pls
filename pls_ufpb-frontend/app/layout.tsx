import type { Metadata } from "next";
import Script from "next/script";
import { Abas } from "@/components/Abas";
import { AvisoValidacao } from "@/components/AvisoValidacao";
import { Cabecalho, Rodape } from "@/components/Marcas";
import { classeDoTema } from "@/lib/tema";
import "./globals.css";

export const metadata: Metadata = {
  title: "Painel PLS UFPB",
  description: "Painel de Sustentabilidade (Plano de Logística Sustentável) da UFPB",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    // tema do LEMA-DS escolhido por projeto em TEMA_DS (lib/tema.ts)
    <html lang="pt-BR" className={classeDoTema()}>
      <head>
        {/* Tipografia Rawline -- Padrao Minimo do Design System de Governo. */}
        <link
          rel="stylesheet"
          href="https://cdngovbr-ds.estaleiro.serpro.gov.br/design-system/fonts/rawline/css/rawline.css"
        />
      </head>
      <body>
        <AvisoValidacao />
        <Cabecalho />
        <Abas />
        {children}
        <Rodape />
        {/* VLibras -- exigido pelas diretrizes de acessibilidade do governo. */}
        <Script src="https://vlibras.gov.br/app/vlibras-plugin.js" strategy="afterInteractive" />
      </body>
    </html>
  );
}
