"use client";

import { useCallback, useEffect, useState } from "react";
import { PillGroup } from "@/components/ui/ds-pill-group";

/** basePath do next.config.ts: fetch do navegador precisa do prefixo. */
const BASE = "/painel-pls/api/formularios";
const CHAVE_TOKEN = "pls-token-formulario";
const CHAVE_NOME = "pls-informado-por";

type Envio = Record<string, string | number | null> & { registrado_em: string; informado_por: string };

type Acao = {
  id: string;
  acao: string;
  tipo: "entrega" | "continua";
  responsavel: string;
  inicio: string;
  fim: string;
  meta: string;
  situacao: string;
  envio_ciclo: Envio | null;
};

type Indicador = {
  id: string;
  indicador: string;
  formula: string;
  unidade: string;
  meta: string;
  responsavel: string;
  calculo: string | null;
  envios: Envio[];
};

type Acesso = { setor: string; ciclo: string; ano_atual: number; primeiro_ano: number; acoes: Acao[]; indicadores: Indicador[] };

const SITUACOES: Record<Acao["tipo"], [string, string][]> = {
  entrega: [
    ["nao_iniciada", "Não iniciada"],
    ["em_andamento", "Em andamento"],
    ["concluida", "Concluída"],
    ["suspensa", "Suspensa"],
    ["cancelada", "Cancelada"],
  ],
  continua: [
    ["realizada_no_ciclo", "Realizada no semestre"],
    ["nao_realizada_no_ciclo", "Não realizada no semestre"],
    ["suspensa", "Suspensa"],
    ["cancelada", "Cancelada"],
  ],
};
const ROTULO_SITUACAO = Object.fromEntries([...SITUACOES.entrega, ...SITUACOES.continua]);
const EXIGE_EVIDENCIA = new Set(["concluida", "realizada_no_ciclo"]);
const EXIGE_JUSTIFICATIVA = new Set(["nao_realizada_no_ciclo", "suspensa", "cancelada"]);

const SITUACAO_PAINEL: Record<string, string> = {
  concluida: "Concluída",
  em_andamento: "Em andamento",
  atrasada: "Atrasada",
  vencida_sem_informacao: "Prazo vencido sem informação",
  a_iniciar: "A iniciar",
  sem_informacao: "Sem informação no ciclo",
  em_dia: "Em dia",
  pendente: "Pendente",
  suspensa: "Suspensa",
  cancelada: "Cancelada",
};

function ler(chave: string): string {
  try {
    return sessionStorage.getItem(chave) ?? "";
  } catch {
    return "";
  }
}

function gravar(chave: string, valor: string | null) {
  try {
    if (valor == null) sessionStorage.removeItem(chave);
    else sessionStorage.setItem(chave, valor);
  } catch {
    /* sem storage (janela privada): o token vale so enquanto a pagina esta aberta */
  }
}

/** "1.234,5" ou "1234.5" -> 1234.5 */
function numeroBr(texto: string): number | null {
  const t = texto.trim();
  if (!t) return null;
  const n = Number(t.includes(",") ? t.replace(/\./g, "").replace(",", ".") : t);
  return Number.isFinite(n) ? n : null;
}

function dataBr(iso: string) {
  return iso.slice(0, 10).split("-").reverse().join("/");
}

async function enviar(token: string, caminho: string, corpo: object): Promise<string | null> {
  const res = await fetch(`${BASE}/${caminho}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-Token-Formulario": token },
    body: JSON.stringify(corpo),
  });
  if (res.ok) return null;
  const j = await res.json().catch(() => ({}));
  if (Array.isArray(j.detail)) return j.detail.map((d: { msg: string }) => d.msg).join("; ");
  return j.detail ?? `Erro ${res.status}`;
}

function Status({ erro, ok }: { erro: string | null; ok: string | null }) {
  if (erro) return <p role="alert" className="msg msg-erro">{erro}</p>;
  if (ok) return <p role="status" className="msg msg-ok">{ok}</p>;
  return null;
}

function FormAcao({ acao, token, ciclo, nome, onEnviado }: { acao: Acao; token: string; ciclo: string; nome: string; onEnviado: () => void }) {
  const ultimo = acao.envio_ciclo;
  const [situacao, setSituacao] = useState(String(ultimo?.situacao ?? ""));
  const [campos, setCampos] = useState<Record<string, string>>({
    percentual: ultimo?.percentual != null ? String(ultimo.percentual) : "",
    evidencia: String(ultimo?.evidencia ?? ""),
    justificativa: String(ultimo?.justificativa ?? ""),
    facilitadores: String(ultimo?.facilitadores ?? ""),
    dificuldades: String(ultimo?.dificuldades ?? ""),
    ajuste_sugerido: String(ultimo?.ajuste_sugerido ?? ""),
    informado_por: String(ultimo?.informado_por ?? nome),
  });
  const [erro, setErro] = useState<string | null>(null);
  const [ok, setOk] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);
  const campo = (k: string) => ({
    id: `${acao.id}-${k}`,
    value: campos[k],
    onChange: (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => setCampos({ ...campos, [k]: e.target.value }),
  });

  async function submeter(e: React.FormEvent) {
    e.preventDefault();
    setErro(null);
    setOk(null);
    setEnviando(true);
    const percentual = acao.tipo === "entrega" ? numeroBr(campos.percentual) : null;
    const falha = await enviar(token, "acompanhamento", { ...campos, acao_id: acao.id, situacao, percentual });
    setEnviando(false);
    if (falha) return setErro(falha);
    gravar(CHAVE_NOME, campos.informado_por);
    setOk(`Registrado para o ciclo ${ciclo}. Aparece no painel na próxima atualização (diária, às 6h).`);
    onEnviado();
  }

  return (
    <article className="card">
      <div className="meta-topo">
        <span className="caption">
          {acao.id} · {acao.tipo === "entrega" ? "Entrega" : "Ação contínua"} · prazo {acao.fim.split("-").reverse().join("/")}
        </span>
        <span className="selo">{SITUACAO_PAINEL[acao.situacao] ?? acao.situacao}</span>
      </div>
      <h3 className="meta-titulo">{acao.acao}</h3>
      <p className="caption">Meta: {acao.meta} · Responsável: {acao.responsavel}</p>
      {ultimo && (
        <p className="caption">
          Último registro no ciclo: {ROTULO_SITUACAO[String(ultimo.situacao)] ?? ultimo.situacao}, por {ultimo.informado_por} em{" "}
          {dataBr(ultimo.registrado_em)}
        </p>
      )}
      <details>
        <summary>{ultimo ? "Atualizar o acompanhamento" : "Registrar o acompanhamento"}</summary>
        <form onSubmit={submeter} className="form">
          <label htmlFor={`${acao.id}-situacao`}>Situação no semestre *</label>
          <select id={`${acao.id}-situacao`} value={situacao} onChange={(e) => setSituacao(e.target.value)} required>
            <option value="">Selecione</option>
            {SITUACOES[acao.tipo].map(([v, r]) => (
              <option key={v} value={v}>
                {r}
              </option>
            ))}
          </select>
          {acao.tipo === "entrega" && (
            <>
              <label htmlFor={`${acao.id}-percentual`}>Percentual executado (0 a 100)</label>
              <input inputMode="decimal" {...campo("percentual")} />
            </>
          )}
          <label htmlFor={`${acao.id}-evidencia`}>
            Evidência {EXIGE_EVIDENCIA.has(situacao) && "*"} <span className="caption">(link, processo SIPAC ou documento)</span>
          </label>
          <input {...campo("evidencia")} required={EXIGE_EVIDENCIA.has(situacao)} />
          <label htmlFor={`${acao.id}-justificativa`}>
            Justificativa {EXIGE_JUSTIFICATIVA.has(situacao) && "*"} <span className="caption">(atraso, suspensão ou não realização)</span>
          </label>
          <textarea rows={2} {...campo("justificativa")} required={EXIGE_JUSTIFICATIVA.has(situacao)} />
          <label htmlFor={`${acao.id}-facilitadores`}>O que facilitou</label>
          <textarea rows={2} {...campo("facilitadores")} />
          <label htmlFor={`${acao.id}-dificuldades`}>O que dificultou</label>
          <textarea rows={2} {...campo("dificuldades")} />
          <label htmlFor={`${acao.id}-ajuste_sugerido`}>Ajuste sugerido ao plano</label>
          <textarea rows={2} {...campo("ajuste_sugerido")} />
          <label htmlFor={`${acao.id}-informado_por`}>Quem informa (nome e setor) *</label>
          <input {...campo("informado_por")} required minLength={3} />
          <button type="submit" disabled={enviando}>{enviando ? "Enviando…" : "Enviar"}</button>
          <Status erro={erro} ok={ok} />
        </form>
      </details>
    </article>
  );
}

function FormIndicador({ ind, token, anos, nome, onEnviado }: { ind: Indicador; token: string; anos: number[]; nome: string; onEnviado: () => void }) {
  const [ano, setAno] = useState(String(anos.at(-2) ?? anos.at(-1)));
  const [valor, setValor] = useState("");
  const [fonte, setFonte] = useState("");
  const [observacao, setObservacao] = useState("");
  const [informadoPor, setInformadoPor] = useState(nome);
  const [erro, setErro] = useState<string | null>(null);
  const [ok, setOk] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);
  const perCapita = ind.calculo === "per_capita";

  async function submeter(e: React.FormEvent) {
    e.preventDefault();
    setErro(null);
    setOk(null);
    const n = numeroBr(valor);
    if (n == null) return setErro("Valor precisa ser um número (ex.: 1.234,5)");
    setEnviando(true);
    const falha = await enviar(token, "valores", {
      indicador_id: ind.id, ano: Number(ano), valor: n, fonte, observacao, informado_por: informadoPor,
    });
    setEnviando(false);
    if (falha) return setErro(falha);
    gravar(CHAVE_NOME, informadoPor);
    setOk(`Valor de ${ano} registrado. Aparece nas metas do PLS na próxima atualização (diária, às 6h).`);
    setValor("");
    onEnviado();
  }

  return (
    <article className="card">
      <div className="meta-topo">
        <span className="caption">{ind.id} · Responsável: {ind.responsavel}</span>
        <span className="selo">{ind.unidade}</span>
      </div>
      <h3 className="meta-titulo">{ind.indicador}</h3>
      <p className="caption">Fórmula: {ind.formula}</p>
      <p className="caption">Meta: {ind.meta}</p>
      {ind.envios.length > 0 && (
        <p className="caption">
          Registros:{" "}
          {ind.envios.map((v) => `${v.ano}: ${String(v.valor).replace(".", ",")} (${v.informado_por}, ${dataBr(v.registrado_em)})`).join(" · ")}
        </p>
      )}
      <details>
        <summary>Informar valor</summary>
        <form onSubmit={submeter} className="form">
          <label htmlFor={`${ind.id}-ano`}>Ano *</label>
          <select id={`${ind.id}-ano`} value={ano} onChange={(e) => setAno(e.target.value)}>
            {anos.map((a) => (
              <option key={a} value={a}>
                {a}
              </option>
            ))}
          </select>
          <label htmlFor={`${ind.id}-valor`}>
            Valor * <span className="caption">({perCapita ? "total do ano; o painel divide pela comunidade acadêmica" : ind.unidade})</span>
          </label>
          <input id={`${ind.id}-valor`} inputMode="decimal" value={valor} onChange={(e) => setValor(e.target.value)} required />
          <label htmlFor={`${ind.id}-fonte`}>Fonte do dado *</label>
          <input id={`${ind.id}-fonte`} value={fonte} onChange={(e) => setFonte(e.target.value)} required minLength={3}
            placeholder="Ex.: relatório do sistema de monitoramento das usinas" />
          <label htmlFor={`${ind.id}-observacao`}>Observação</label>
          <textarea id={`${ind.id}-observacao`} rows={2} value={observacao} onChange={(e) => setObservacao(e.target.value)} />
          <label htmlFor={`${ind.id}-informado`}>Quem informa (nome e setor) *</label>
          <input id={`${ind.id}-informado`} value={informadoPor} onChange={(e) => setInformadoPor(e.target.value)} required minLength={3} />
          <button type="submit" disabled={enviando}>{enviando ? "Enviando…" : "Enviar"}</button>
          <Status erro={erro} ok={ok} />
        </form>
      </details>
    </article>
  );
}

export default function Formularios() {
  const [token, setToken] = useState("");
  const [digitado, setDigitado] = useState("");
  const [acesso, setAcesso] = useState<Acesso | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [aba, setAba] = useState<"acoes" | "indicadores">("acoes");
  const [nome, setNome] = useState("");

  const carregar = useCallback(async (t: string) => {
    setErro(null);
    const res = await fetch(`${BASE}/acesso`, { headers: { "X-Token-Formulario": t }, cache: "no-store" });
    if (!res.ok) {
      const j = await res.json().catch(() => ({}));
      setAcesso(null);
      setToken("");
      gravar(CHAVE_TOKEN, null);
      return setErro(j.detail ?? `Erro ${res.status}`);
    }
    setAcesso(await res.json());
    setToken(t);
    gravar(CHAVE_TOKEN, t);
  }, []);

  useEffect(() => {
    setNome(ler(CHAVE_NOME));
    const salvo = ler(CHAVE_TOKEN);
    if (salvo) void carregar(salvo);
  }, [carregar]);

  if (!acesso) {
    return (
      <form
        className="card form"
        onSubmit={(e) => {
          e.preventDefault();
          void carregar(digitado.trim());
        }}
      >
        <label htmlFor="token">Token de acesso do setor</label>
        <input id="token" type="password" autoComplete="off" value={digitado} onChange={(e) => setDigitado(e.target.value)} required />
        <p className="caption">O token é entregue pela Comissão Gestora do PLS a cada setor responsável.</p>
        <button type="submit">Entrar</button>
        <Status erro={erro} ok={null} />
      </form>
    );
  }

  const anos = Array.from({ length: acesso.ano_atual - acesso.primeiro_ano + 1 }, (_, i) => acesso.primeiro_ano + i);
  const pendentes = acesso.acoes.filter((a) => !a.envio_ciclo).length;

  return (
    <>
      <div className="meta-topo">
        <p>
          Setor: <strong>{acesso.setor}</strong> · ciclo {acesso.ciclo} · {pendentes} de {acesso.acoes.length} ações sem
          registro no ciclo
        </p>
        <button
          type="button"
          className="botao-secundario"
          onClick={() => {
            gravar(CHAVE_TOKEN, null);
            setAcesso(null);
            setToken("");
            setDigitado("");
          }}
        >
          Sair
        </button>
      </div>
      <nav className="mb-5 max-w-full" aria-label="Formulário">
        <PillGroup
          label="Formulário"
          items={[
            { value: "acoes", label: "Ações do plano", count: acesso.acoes.length },
            { value: "indicadores", label: "Indicadores informados", count: acesso.indicadores.length },
          ]}
          value={aba}
          onChange={(v) => v && setAba(v as "acoes" | "indicadores")}
          size="sm"
          locale="pt-BR"
        />
      </nav>
      {aba === "acoes" &&
        (acesso.acoes.length ? (
          acesso.acoes.map((a) => (
            <FormAcao key={a.id} acao={a} token={token} ciclo={acesso.ciclo} nome={nome} onEnviado={() => void carregar(token)} />
          ))
        ) : (
          <p className="caption">Nenhuma ação do plano sob responsabilidade deste setor.</p>
        ))}
      {aba === "indicadores" &&
        (acesso.indicadores.length ? (
          acesso.indicadores.map((i) => (
            <FormIndicador key={i.id} ind={i} token={token} anos={anos} nome={nome} onEnviado={() => void carregar(token)} />
          ))
        ) : (
          <p className="caption">Nenhum indicador informado sob responsabilidade deste setor.</p>
        ))}
    </>
  );
}
