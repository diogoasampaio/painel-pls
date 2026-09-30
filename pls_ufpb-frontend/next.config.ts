import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Sub-rota do Nginx na VM A (ao lado de /prpg-avaliacao)
  basePath: "/painel-pls",
  experimental: {
    // componentes do LEMA-DS importam de "radix-ui" (pacote-barril): sem isto, uma
    // página que só usa o Slot do botão leva todos os primitivos Radix ao navegador
    optimizePackageImports: ["radix-ui"],
  },
};

export default nextConfig;
