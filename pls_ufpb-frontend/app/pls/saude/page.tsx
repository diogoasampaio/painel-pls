import { Kpi } from "@/components/Kpi";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge, type BadgeProps } from "@/components/ui/ds-badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { getSaude, type NivelSaude } from "@/lib/api";

export const dynamic = "force-dynamic";

const NIVEL: Record<NivelSaude, { texto: string; variante: BadgeProps["variant"] }> = {
  erro: { texto: "Erro", variante: "destructive" },
  atencao: { texto: "Atenção", variante: "warning" },
  info: { texto: "Informativo", variante: "secondary" },
  ok: { texto: "Em dia", variante: "success" },
};

function dataHora(iso: string) {
  const [d, h] = iso.split("T");
  return `${d.split("-").reverse().join("/")} ${h?.slice(0, 5) ?? ""}`;
}

/** O que a última carga automática deixou pendente, com o que fazer em cada caso. */
export default async function SaudeCarga() {
  const { execucao, itens, historico } = await getSaude();
  const conta = (n: NivelSaude) => itens.filter((i) => i.nivel === n).length;

  return (
    <main className="container">
      <h1 className="page-title">Saúde da carga</h1>
      <p className="caption">
        Conferência feita no fim de cada carga mensal: fontes que falharam, meses sem dado, arquivos que precisam de
        cadastro e informações pendentes dos setores. Erros e pontos de atenção também vão por e-mail para a equipe.
      </p>

      {!execucao ? (
        <Card size="sm">
          <CardContent className="text-sm text-muted-foreground">Nenhuma carga registrada ainda.</CardContent>
        </Card>
      ) : (
        <div className="flex flex-col gap-4">
          <div className="grid grid-cols-[repeat(auto-fill,minmax(14rem,1fr))] gap-4">
            <Kpi rotulo="Última carga" valor={dataHora(execucao)} icone="relogio" />
            {/* número colorido só quando há pendência: zero erro não é alarme */}
            <Kpi rotulo="Erro" valor={conta("erro")} icone="erro" destaque={conta("erro") ? "text-destructive" : undefined} />
            <Kpi rotulo="Atenção" valor={conta("atencao")} icone="atencao" />
            <Kpi rotulo="Em dia" valor={conta("ok")} icone="ok" destaque="text-success" />
          </div>

          {itens.map((i) => (
            <Card key={i.verificacao + i.modulo} size="sm">
              <CardHeader>
                <CardDescription className="flex flex-wrap items-center gap-2">
                  <Badge variant={NIVEL[i.nivel].variante}>{NIVEL[i.nivel].texto}</Badge>
                  Módulo {i.modulo}
                </CardDescription>
                <CardTitle>{i.titulo}</CardTitle>
              </CardHeader>
              {(i.acao_sugerida || i.detalhe.length > 0) && (
                <CardContent className="flex flex-col gap-2 text-sm">
                  {i.acao_sugerida && (
                    <p>
                      <span className="text-muted-foreground">O que fazer:</span> {i.acao_sugerida}
                    </p>
                  )}
                  {i.detalhe.length > 0 && (
                    <details className="text-muted-foreground">
                      <summary className="cursor-pointer">Itens ({i.quantidade})</summary>
                      <ul className="mt-2 flex list-disc flex-col gap-1 pl-5">
                        {i.detalhe.map((d) => (
                          <li key={d}>{d}</li>
                        ))}
                      </ul>
                    </details>
                  )}
                </CardContent>
              )}
            </Card>
          ))}

          {historico.length > 1 && (
            <section className="mt-4 flex flex-col gap-2">
              <h2 className="section-title">Cargas anteriores</h2>
              <Card size="sm">
                <CardContent>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Carga</TableHead>
                        <TableHead className="text-right">Erros</TableHead>
                        <TableHead className="text-right">Atenção</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {historico.map((h) => (
                        <TableRow key={h.execucao} className="h-10">
                          <TableCell className="tabular-nums">{dataHora(h.execucao)}</TableCell>
                          <TableCell className="text-right tabular-nums">
                            {h.erro ? <Badge variant="destructive">{h.erro}</Badge> : 0}
                          </TableCell>
                          <TableCell className="text-right tabular-nums">
                            {h.atencao ? <Badge variant="warning">{h.atencao}</Badge> : 0}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </CardContent>
              </Card>
            </section>
          )}
        </div>
      )}
    </main>
  );
}
