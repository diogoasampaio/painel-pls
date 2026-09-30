import { PainelPage } from "@/components/PainelPage";

type Props = {
  params: Promise<{ slug: string }>;
  searchParams: Promise<Record<string, string | undefined>>;
};

export default async function Page({ params, searchParams }: Props) {
  const { slug } = await params;
  return <PainelPage slug={slug} q={await searchParams} base={`/pls/${slug}`} />;
}
