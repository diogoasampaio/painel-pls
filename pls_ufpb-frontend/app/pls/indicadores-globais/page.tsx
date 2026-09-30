import { PainelPage } from "@/components/PainelPage";

type Props = { searchParams: Promise<Record<string, string | undefined>> };

/** Visao consolidada = painel "visao-geral" da API (todos os temas, quebra por tema). */
export default async function IndicadoresGlobais({ searchParams }: Props) {
  return <PainelPage slug="visao-geral" q={await searchParams} base="/pls/indicadores-globais" />;
}
