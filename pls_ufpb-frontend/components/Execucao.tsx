"use client";

import { CardStat } from "@/components/ui/ds-card-stat";
import { Card, CardContent, CardDescription, CardHeader } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { Execucao, FaixaCodigo } from "@/lib/api";
import { FAIXA_COR } from "@/lib/faixas";
import { cn } from "@/lib/utils";

const num = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 1 });
const pct = (v: number | null | undefined) => (v == null ? "—" : `${num.format(v)}%`);

/** Faixas com alcance numerico entram na barra; as demais aparecem so na legenda. */
const COM_ALCANCE: FaixaCodigo[] = ["atingida", "proxima", "progresso", "distante"];

/** "75–99%", "< 50%", "100%" a partir dos minimos de ref/faixas_execucao.csv */
function intervalo(faixas: Execucao["faixas"], f: Execucao["faixas"][number]): string | null {
  if (f.alcance_minimo == null || !COM_ALCANCE.includes(f.codigo)) return null;
  const acima = faixas
    .filter((o) => o.alcance_minimo != null && o.alcance_minimo > f.alcance_minimo!)
    .map((o) => o.alcance_minimo!)
    .sort((a, b) => a - b)[0];
  if (acima == null) return `${f.alcance_minimo}%`;
  if (f.alcance_minimo === 0) return `< ${acima}%`;
  return `${f.alcance_minimo}–${acima - 1}%`;
}

/**
 * Distribuicao dos indicadores por faixa (barra empilhada). O LEMA-DS nao tem
 * barra de contagens (o ds-risk-level-bar e escala com marcador): fica aqui,
 * so com tokens (FAIXA_COR). A largura de cada segmento e proporcional a contagem.
 */
function BarraFaixas({ faixas, contagem, rotulo }: { faixas: Execucao["faixas"]; contagem: Record<string, number>; rotulo: string }) {
  const total = faixas.reduce((s, f) => s + (contagem[f.codigo] ?? 0), 0);
  if (!total) return <span className="text-muted-foreground">—</span>;
  return (
    <div
      className="flex h-6 min-w-32 overflow-hidden rounded-md"
      role="img"
      aria-label={`${rotulo}: ${faixas.map((f) => `${f.faixa} ${contagem[f.codigo] ?? 0}`).join(", ")}`}
    >
      {faixas.map((f) =>
        contagem[f.codigo] ? (
          <span
            key={f.codigo}
            className={cn("flex min-w-6 items-center justify-center text-xs font-semibold tabular-nums", FAIXA_COR[f.codigo])}
            style={{ flexGrow: contagem[f.codigo] }}
            title={`${f.faixa}: ${contagem[f.codigo]}`}
          >
            {contagem[f.codigo]}
          </span>
        ) : null,
      )}
    </div>
  );
}

/**
 * Indice sintetico de execucao do PLS: alcance das metas dos indicadores
 * (media por eixo) combinado com o cumprimento do plano de acoes, mais a
 * distribuicao dos indicadores por faixa de execucao.
 */
export default function PainelExecucao({ dados }: { dados: Execucao }) {
  const atual = dados.serie.find((s) => s.ano === dados.ano);
  if (!atual) return null;
  const p = dados.parametros;
  const pesos = `${num.format(p.peso_metas * 100)}% metas + ${num.format(p.peso_acoes * 100)}% ações`;
  const anoFaixas = atual.ano_metas ?? atual.ano;
  const avaliados =
    atual.ano_metas != null ? (dados.serie.find((s) => s.ano === atual.ano_metas)?.n_avaliados ?? 0) : atual.n_avaliados;

  return (
    <section className="my-6 flex flex-col gap-4" aria-labelledby="titulo-execucao">
      <h2 id="titulo-execucao" className="section-title">Execução do plano</h2>

      <div className="grid grid-cols-[repeat(auto-fill,minmax(14rem,1fr))] gap-4">
        {/* ano na descrição: no rótulo, o truncate do DS corta "· 2026" */}
        <CardStat label="Índice sintético de execução" value={pct(atual.indice_sintetico)} description={`${atual.ano} · ${pesos}`} size="md" locale="pt-BR" />
        <CardStat
          label={`Alcance das metas${atual.ano_metas && atual.ano_metas !== atual.ano ? ` (${atual.ano_metas})` : ""}`}
          value={pct(atual.indice_metas_usado)}
          description={`Média ${p.agregacao_metas === "eixo" ? "por eixo" : "dos indicadores"}, com cada meta limitada a 100%`}
          size="md"
          locale="pt-BR"
        />
        <CardStat
          label="Cumprimento das ações"
          value={pct(atual.indice_acoes)}
          description="Concluídas, em dia ou em andamento com evidência, sobre as exigíveis"
          size="md"
          locale="pt-BR"
        />
        <CardStat
          label="Cobertura da avaliação"
          value={`${avaliados} de ${atual.n_com_meta}`}
          description="Indicadores com meta que já têm valor comparável"
          size="md"
          locale="pt-BR"
        />
      </div>

      <Card size="sm">
        <CardHeader>
          <CardDescription>Indicadores por faixa de execução · {anoFaixas}</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          <BarraFaixas
            faixas={dados.faixas}
            contagem={(dados.serie.find((s) => s.ano === anoFaixas) ?? atual).faixas}
            rotulo="Indicadores por faixa"
          />
          <ul className="flex flex-wrap gap-x-4 gap-y-1 text-sm">
            {dados.faixas.map((f) => (
              <li key={f.codigo} className="flex items-center gap-1.5">
                <span className={cn("size-3 rounded-full", FAIXA_COR[f.codigo])} aria-hidden="true" />
                {f.faixa}
                {intervalo(dados.faixas, f) && <span className="text-muted-foreground">({intervalo(dados.faixas, f)})</span>}
              </li>
            ))}
          </ul>
        </CardContent>
      </Card>

      <Card size="sm">
        <CardContent>
          <details className="flex flex-col gap-4">
            <summary className="cursor-pointer font-medium">Por eixo ({dados.ano_detalhe}) e série histórica</summary>
            <div className="mt-3 flex flex-col gap-6">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Eixo</TableHead>
                    <TableHead className="text-right">Alcance das metas</TableHead>
                    <TableHead className="text-right">Avaliados</TableHead>
                    <TableHead>Faixas</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {dados.eixos.map((e) => (
                    <TableRow key={e.eixo_pls} className="h-10">
                      <TableCell className="whitespace-normal">
                        {e.eixo_pls} · {e.eixo ?? (e.eixo_pls === "transversal" ? "Gestão do plano" : "")}
                      </TableCell>
                      <TableCell className="text-right tabular-nums">{pct(e.indice_metas)}</TableCell>
                      <TableCell className="text-right tabular-nums">
                        {e.n_avaliados} de {e.n_com_meta}
                      </TableCell>
                      <TableCell className="min-w-40">
                        <BarraFaixas faixas={dados.faixas} contagem={e.faixas} rotulo={`Eixo ${e.eixo_pls}`} />
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Ano</TableHead>
                    <TableHead className="text-right">Índice sintético</TableHead>
                    <TableHead className="text-right">Metas</TableHead>
                    <TableHead className="text-right">Ações</TableHead>
                    <TableHead>Componentes</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {dados.serie.map((s) => (
                    <TableRow key={s.ano} className="h-10">
                      <TableCell className="tabular-nums">
                        {s.ano}
                        {!s.ano_fechado && " (em curso)"}
                      </TableCell>
                      <TableCell className="text-right tabular-nums">{pct(s.indice_sintetico)}</TableCell>
                      <TableCell className="text-right tabular-nums">
                        {pct(s.indice_metas_usado)}
                        {s.ano_metas && s.ano_metas !== s.ano ? ` (de ${s.ano_metas})` : ""}
                      </TableCell>
                      <TableCell className="text-right tabular-nums">{pct(s.indice_acoes)}</TableCell>
                      <TableCell>{s.componentes ? s.componentes.replace("acoes", "ações").replace("+", " + ") : "—"}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
              <p className="text-sm text-muted-foreground">
                O alcance compara o valor do ano com a meta: redução ou aumento obtido sobre o previsto, ou valor sobre o
                mínimo. Piora conta como 0% e metas superadas contam como 100%. Ano parcial ou de linha de base não entra.
                Pesos e faixas ficam em ref/indice_execucao.csv e ref/faixas_execucao.csv.
              </p>
            </div>
          </details>
        </CardContent>
      </Card>
    </section>
  );
}
