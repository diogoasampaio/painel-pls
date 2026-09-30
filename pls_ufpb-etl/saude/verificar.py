"""Saude da carga -> pls_saude_carga + alerta por e-mail.

Roda no fim da carga mensal (run.py mensal) e confere, nos parquet de
data/processed/ e nas tabelas de ref/, o que costuma exigir alguem:

  modulo_falhou            modulo que levantou excecao na carga (erro)
  despesas_atraso          ultimo mes com despesas mais antigo que o esperado
  despesas_dias            dias que o servidor da CGU recusou (arquivo indisponivel)
  faturas_processos        processos sem fatura legivel ou nao achados no SIPAC
  faturas_numeros          numero de processo do Portal corrigido pela base aberta de processos
  faturas_anomalias        ligacao/UC grande cujo consumo anual mudou mais de 50% (medidor,
                           fonte alternativa ou erro -- distorce as metas e o indice)
  faturas_meses            mes sem leitura de energia, agua, combustivel ou residuos
  itens_quantidade         copos, papel A4 e toner sem quantidade (sem preco da compra) ou com
                           unidade presumida (preco do PNCP incompativel com a unidade)
  compras_documentos       contratacao (licitacao ou dispensa) sem edital/TR legivel no PNCP ou com erro de leitura
  evg_bimestre             bimestre da EVG publicado e ainda sem id em ref/evg_recursos.csv
  gee_fator                meses de energia sem fator mensal do SIN publicado (modulo fator_sin)
  comunidade_ufpb          contagem da comunidade academica (ref/comunidade_ufpb.csv) sem o ano anterior
  inep_censo               censo da educacao superior novo que ainda nao foi carregado (reserva da contagem)
  ipca_atraso              IPCA sem o mes anterior
  cnpj_sem_cadastro        fatia do pago a fornecedores sem porte/UF (cadastro desatualizado)
  acoes_acompanhamento     acoes vencidas sem informacao / sem acompanhamento no ciclo
  metas_informados         indicadores informados sem valor do ultimo ano fechado

Cada verificacao gera uma linha com nivel erro | atencao | info | ok,
titulo, detalhe (itens concretos) e a acao sugerida. A colecao guarda o
historico (chave `execucao`); a API mostra a ultima.

E-mail: com SMTP_HOST e ALERTA_EMAILS no .env, envia o resumo quando ha
erro ou atencao. Sem essas variaveis, so imprime.
"""

from __future__ import annotations

import os
import smtplib
from datetime import date, datetime
from email.message import EmailMessage

import numpy as np
import pandas as pd

from common import comunidade, config
from common.mongo import replace_by
from common.storage import load_processed, read_json, save_processed

COLLECTION = "pls_saude_carga"
NIVEIS = ("erro", "atencao", "info", "ok")
TIPOS_FATURA = {"energia": "energia (Energisa)", "agua": "água (CAGEPA)", "combustivel": "combustível (frota)",
                "residuos": "resíduos de saúde"}
LIMITE_SEM_CADASTRO = 5.0  # % do pago no ano
MAX_ITENS = 25


def _mes(d: date, menos: int = 0) -> str:
    n = d.year * 12 + d.month - 1 - menos
    return f"{n // 12}-{n % 12 + 1:02d}"


def _linha(codigo: str, modulo: str, nivel: str, titulo: str, itens: list[str] | None = None, acao: str = "") -> dict:
    itens = itens or []
    return {"verificacao": codigo, "modulo": modulo, "nivel": nivel, "titulo": titulo, "quantidade": len(itens),
            "detalhe": itens[:MAX_ITENS] + ([f"... e mais {len(itens) - MAX_ITENS}"] if len(itens) > MAX_ITENS else []),
            "acao_sugerida": acao}


# ---------------------------------------------------------------- verificacoes

def despesas(hoje: date) -> list[dict]:
    out = []
    df = load_processed("pls_despesas")
    esperado = _mes(hoje, 1)  # o Portal publica o dia anterior; o mes passado tem de estar la
    ultimo = df["periodo"].max() if not df.empty else None
    if not ultimo or ultimo < esperado:
        out.append(_linha("despesas_atraso", "despesas", "erro", f"Despesas só até {ultimo or '—'} (esperado {esperado})",
                          acao="Ver o log da carga de despesas; o servidor da CGU pode ter bloqueado o IP (HTTP 403/405)."))
    else:
        out.append(_linha("despesas_atraso", "despesas", "ok", f"Despesas carregadas até {ultimo}"))
    indisp = []
    base = config.RAW_DIR / "portal_bulk"
    for ano in {hoje.year, hoje.year - 1}:
        for arq in sorted((base / str(ano)).glob("*.json")):
            if (hoje - date.fromisoformat(arq.stem)).days <= 120:
                cache = read_json(arq)
                if isinstance(cache, dict) and cache.get("indisponivel"):
                    indisp.append(f"{arq.stem} (HTTP {cache['indisponivel']})")
    out.append(_linha("despesas_dias", "despesas", "atencao" if indisp else "ok",
                      f"{len(indisp)} dia(s) recusados pelo servidor da CGU nos últimos 120 dias" if indisp
                      else "Nenhum dia indisponível no servidor da CGU", indisp,
                      "Tentar de novo na próxima carga; se persistir, conferir o total do mês no Tesouro Gerencial." if indisp else ""))
    return out


def faturas(hoje: date) -> list[dict]:
    df = load_processed("pls_faturas")
    if df.empty:
        return [_linha("faturas_processos", "faturas", "erro", "Nenhuma fatura processada")]
    out = []
    proc = df.drop_duplicates("processo")
    ruins = proc[~proc["status"].isin(["ok", "fora_escopo"])].sort_values("data_pagamento", ascending=False)
    rotulo = {"sem_fatura_legivel": "sem fatura legível", "processo_nao_encontrado": "não achado no SIPAC"}
    cand = ruins["candidatos"] if "candidatos" in ruins else pd.Series(None, index=ruins.index)
    itens = [f"{r.processo} · {r.tipo} · {rotulo.get(r.status, r.status)} · pago em {r.data_pagamento or '—'}"
             + (f" · candidatos na base de processos: {c}" if isinstance(c, str) else "")
             for r, c in zip(ruins.itertuples(), cand)]
    out.append(_linha("faturas_processos", "faturas", "atencao" if itens else "ok",
                      f"{len(itens)} processo(s) de pagamento sem leitura da fatura" if itens else "Todos os processos lidos",
                      itens, "Abrir o processo no SIPAC. Número digitado errado no Portal sem candidato único: conferir "
                             "os candidatos e incluir em ref/processos_corrigidos.csv. Layout novo de fatura: pedir "
                             "leitor novo." if itens else ""))
    if "correcao" in proc:
        auto = proc[proc["correcao"] == "automatica"]
        out.append(_linha("faturas_numeros", "faturas", "info" if len(auto) else "ok",
                          f"{len(auto)} número(s) de processo corrigido(s) pela base de processos da UFPB" if len(auto)
                          else "Nenhum número de processo corrigido automaticamente",
                          [f"{r.processo_portal} (Portal) → {r.processo} · {r.tipo} · pago em {r.data_pagamento or '—'}"
                           for r in auto.itertuples()],
                          "Digitado errado no Portal, com DV inválido; o candidato único (mesmo ano, mesmo DV e "
                          "assunto do tipo) foi usado. Conferir no SIPAC." if len(auto) else ""))
    ok = df[df["status"] == "ok"]
    # faturas chegam com ~2 meses de atraso (referencia -> pagamento -> Portal)
    janela = [_mes(hoje, k) for k in range(14, 2, -1)]
    faltas = []
    for tipo, nome in TIPOS_FATURA.items():
        meses = set(ok.loc[ok["tipo"] == tipo, "periodo"].dropna())
        faltas += [f"{nome}: {m}" for m in janela if m not in meses]
    out.append(_linha("faturas_meses", "faturas", "atencao" if faltas else "ok",
                      f"{len(faltas)} mês(es) sem consumo lido de {janela[0]} a {janela[-1]}" if faltas
                      else f"Consumo lido em todos os meses de {janela[0]} a {janela[-1]}", faltas,
                      "Conferir se o pagamento do mês saiu no Portal e se o processo tem a fatura anexada." if faltas else ""))
    return out


def anomalias(hoje: date, limite: float = 50.0, fatia_min: float = 5.0) -> list[dict]:
    """UC com pelo menos `fatia_min`% do consumo do tipo cujo total anual variou mais de
    `limite`% entre os dois ultimos anos fechados."""
    df = load_processed("pls_faturas")
    ok = df[(df["status"] == "ok") & df["tipo"].isin(["energia", "agua"])].copy()
    a1, a0 = hoje.year - 1, hoje.year - 2
    ok["qtd"] = np.where(ok["tipo"] == "agua", ok.get("m3"), ok.get("kwh"))
    itens = []
    for tipo, g in ok[ok["ano"].isin([a0, a1])].groupby("tipo"):
        p = g.pivot_table(index="uc", columns="ano", values="qtd", aggfunc="sum").reindex(columns=[a0, a1]).fillna(0)
        total = p[a0].sum()
        grandes = p[p[a0] >= total * fatia_min / 100]
        for uc, r in grandes.iterrows():
            var = 100 * (r[a1] / r[a0] - 1) if r[a0] else None
            if var is not None and abs(var) > limite:
                un = "m³" if tipo == "agua" else "kWh"
                itens.append(f"{TIPOS_FATURA[tipo]} · UC {uc}: {r[a0]:,.0f} → {r[a1]:,.0f} {un} ({var:+.0f}% de {a0} para {a1})"
                             .replace(",", "."))
    return [_linha("faturas_anomalias", "faturas", "atencao" if itens else "ok",
                   f"{len(itens)} ligação(ões) grande(s) com consumo anual variando mais de {limite:.0f}%" if itens
                   else "Sem variação anômala nas ligações grandes", itens,
                   "Confirmar com a SINFRA (hidrômetro/medidor, poço ou geração própria, obra, vazamento). "
                   "A variação entra direto nas metas e no índice de execução." if itens else "")]


def compras(hoje: date) -> list[dict]:
    df = load_processed("pls_compras")
    if df.empty:
        return [_linha("compras_documentos", "compras", "info", "Contratações do PNCP ainda não carregadas")]
    df = df[(df["ano"] >= hoje.year - 1) & ~df["modalidade"].str.upper().str.startswith("INEXIG")]
    ruins = df[df["nivel_sustentabilidade"].isin(["sem_texto", "sem_documento", "erro"])].sort_values("data_publicacao")
    rot = {"sem_texto": "PDF sem texto (escaneado)", "sem_documento": "sem edital/TR publicado", "erro": "erro de leitura"}
    itens = [f"{r.controle} · {r.modalidade} · {rot[r.nivel_sustentabilidade]} · {(r.objeto or '')[:70]}"
             for r in ruins.itertuples()]
    pct = 100 * len(ruins) / len(df) if len(df) else 0
    nivel = "atencao" if pct > 10 or (ruins["nivel_sustentabilidade"] == "erro").any() else ("info" if itens else "ok")
    return [_linha("compras_documentos", "compras", nivel,
                   f"{len(itens)} contratação(ões) sem edital/TR legível desde {hoje.year - 1} ({pct:.0f}%)" if itens
                   else "Editais e TRs legíveis em todas as contratações", itens,
                   "Erro de leitura: tenta de novo na próxima carga. PDF escaneado ou sem TR publicado: o N10 não "
                   "avalia essas contratações (ficam fora da razão)." if itens else "")]


def evg(hoje: date) -> list[dict]:
    rec = pd.read_csv(config.REF_DIR / "evg_recursos.csv", sep=";", dtype=str)
    cadastrados = {(int(a), int(b)) for a, b in zip(rec["ano"], rec["bimestre"])}
    # a ENAP publica o bimestre ~1 mes depois do fim
    limite = _mes(hoje, 2)
    faltam = []
    for ano in range(2023, hoje.year + 1):
        for bim in range(1, 7):
            fim = f"{ano}-{bim * 2:02d}"
            if fim <= limite and (ano, bim) not in cadastrados:
                faltam.append(f"{ano} · bimestre {bim} ({fim[:4]}/{bim * 2 - 1:02d}–{bim * 2:02d})")
    return [_linha("evg_bimestre", "evg", "atencao" if faltam else "ok",
                   f"{len(faltam)} bimestre(s) da EVG sem arquivo cadastrado" if faltam else "Arquivos da EVG em dia",
                   faltam, "Procurar o CSV do bimestre no dados.gov.br (conjunto da EVG) e pôr o id do Google Drive "
                           "em ref/evg_recursos.csv. Alguns bimestres a ENAP nunca publicou." if faltam else "")]


MESES_ATRASO_FATOR = 4  # o MCTI publica o fator mensal com 1 a 3 meses de atraso


def gee() -> list[dict]:
    """Meses de energia (escopo 2) sem fator mensal publicado pelo MCTI (modulo fator_sin)."""
    sin = load_processed("pls_fator_sin")
    ind = load_processed("pls_indicadores")
    if ind.empty:
        return []
    esc2 = (ind["metrica"] == "emissoes_kgco2e") & ind["subtema"].str.startswith("Escopo 2")
    meses = sorted(set(ind.loc[esc2, "periodo"]))
    if sin.empty:
        return [_linha("gee_fator", "fator_sin", "atencao", "Fator mensal do SIN não carregado", [],
                       "Rodar `python run.py fator_sin` (planilha de inventários corporativos do MCTI).")]
    publicados = set(sin["periodo"])
    prov = [m for m in meses if m not in publicados]
    atrasado = len(prov) >= MESES_ATRASO_FATOR
    return [_linha("gee_fator", "fator_sin", "atencao" if atrasado else ("info" if prov else "ok"),
                   f"{len(prov)} mês(es) de energia com fator do SIN provisório (MCTI publicou até "
                   f"{sin['periodo'].max()})" if prov else f"Fator do SIN publicado até {sin['periodo'].max()}",
                   prov, "Conferir se o MCTI publicou planilha nova na página de fatores de emissão do SIRENE; "
                         "se o link mudou de formato, ajustar fator_sin/load_fator_sin.py." if atrasado else "")]


def itens_quantidade(hoje: date) -> list[dict]:
    q = load_processed("pls_itens_quantidade")
    if q.empty:
        return [_linha("itens_quantidade", "quantidades", "info", "Quantidades de copos, papel e toner ainda não calculadas",
                       acao="Rodar `python run.py quantidades`.")]
    q = q[q["ano"] >= hoje.year - 1]
    sem = q[q["quantidade"].isna()]
    pct = 100 * sem["valor"].sum() / q["valor"].sum() if q["valor"].sum() else 0
    pres = q[q["unidade_presumida"].fillna(False).astype(bool)]
    itens = [f"{f}: R$ {v:,.0f} sem quantidade".replace(",", ".") for f, v in sem.groupby("familia")["valor"].sum().items()]
    itens += sorted({f"{r.familia} {r.compra or 'sem compra no PNCP'} item {int(r.numero_item) if r.numero_item == r.numero_item else '?'}: "
                     f"embalagem presumida de {r.por_embalagem:.0f}" for r in pres.itertuples()})
    nivel = "atencao" if pct > 20 else ("info" if itens else "ok")
    return [_linha("itens_quantidade", "quantidades", nivel,
                   f"{pct:.0f}% do valor de copos, papel e toner desde {hoje.year - 1} sem quantidade; "
                   f"{len(pres)} item(ns) com embalagem presumida", itens,
                   "Conferir no termo de referência a embalagem dos itens presumidos e registrar em "
                   "ref/itens_unidade_correcao.csv." if itens else "")]


def comunidade_ufpb(hoje: date) -> list[dict]:
    tab = comunidade.ufpb()
    ufpb = tab[tab["fonte"] == comunidade.FONTE_UFPB]
    ultimo = int(ufpb.index.max()) if not ufpb.empty else None
    # a contagem do ano A fica pronta no inicio de A+1
    esperado = hoje.year - 1 if hoje.month >= 4 else hoje.year - 2
    nivel = "ok" if ultimo and ultimo >= esperado else "atencao"
    return [_linha("comunidade_ufpb", "comunidade", nivel, f"Contagem da comunidade acadêmica da UFPB até {ultimo or '—'}",
                   acao="" if nivel == "ok" else
                   f"Pedir a planilha com {esperado} (discentes, docentes, técnicos e terceirizados) e rodar "
                   "`python -m common.comunidade <planilha.xlsx>`; até lá os indicadores por pessoa usam o último ano.")]


def inep(hoje: date) -> list[dict]:
    com = load_processed("pls_comunidade")
    ultimo = int(com["ano"].max()) if not com.empty else None
    # o censo do ano A sai no fim do ano A+1; e so reserva da contagem da UFPB, por isso no maximo info
    esperado = hoje.year - 2 if hoje.month >= 11 else hoje.year - 3
    nivel = "ok" if ultimo and ultimo >= esperado else "info"
    return [_linha("inep_censo", "inep", nivel, f"Censo da Educação Superior carregado até {ultimo or '—'}",
                   acao="" if nivel == "ok" else "Rodar `python run.py inep` com o censo novo (reserva da comunidade acadêmica).")]


def ipca(hoje: date) -> list[dict]:
    df = load_processed("pls_ipca")
    ultimo = df["periodo"].max() if not df.empty else None
    esperado = _mes(hoje, 2 if hoje.day < 12 else 1)  # IBGE divulga por volta do dia 10
    nivel = "ok" if ultimo and ultimo >= esperado else "atencao"
    return [_linha("ipca_atraso", "ipca", nivel, f"IPCA até {ultimo or '—'}",
                   acao="" if nivel == "ok" else "Conferir a série 433 do BCB/SGS.")]


def cnpj(hoje: date) -> list[dict]:
    pag = load_processed("pls_pagamentos_pj")
    if pag.empty or "subtema" not in pag:
        return [_linha("cnpj_sem_cadastro", "cnpj", "info", "Cadastro de fornecedores ainda não carregado")]
    ano = pag[pag["ano"] == pag["ano"].max()]
    base = ano[~ano["subtema"].str.startswith("Instituição financeira")]
    sem = base[base["subtema"] == "Sem cadastro na Receita"]
    pct = 100 * sem["valor"].sum() / base["valor"].sum() if base["valor"].sum() else 0.0
    itens = sorted(sem["cnpj"].unique())
    nivel = "atencao" if pct > LIMITE_SEM_CADASTRO else ("info" if itens else "ok")
    return [_linha("cnpj_sem_cadastro", "cnpj", nivel,
                   f"{pct:.1f}% do pago a fornecedores em {int(ano['ano'].max())} sem porte/UF ({len(itens)} CNPJ)",
                   itens, "Rodar `python run.py cnpj --refazer` para reler o cadastro da Receita." if nivel == "atencao" else "")]


def acoes(hoje: date) -> list[dict]:
    df = load_processed("pls_acoes")
    if df.empty:
        return []
    out = []
    vencidas = df[df["situacao"].isin(["vencida_sem_informacao", "atrasada"])]
    itens = [f"{r.id} · {r.responsavel} · prazo {r.fim} · {r.situacao.replace('_', ' ')}" for r in vencidas.itertuples()]
    out.append(_linha("acoes_vencidas", "acoes", "atencao" if itens else "ok",
                      f"{len(itens)} ação(ões) com prazo vencido" if itens else "Nenhuma ação vencida", itens,
                      "Cobrar do responsável o registro no formulário de acompanhamento." if itens else ""))
    sem = df[df["exigivel"] & (df["situacao"] == "sem_informacao")]
    fim_ciclo = hoje.month in (6, 12)
    nivel = ("atencao" if fim_ciclo else "info") if len(sem) else "ok"
    resp = sem.groupby("responsavel").size().sort_values(ascending=False)
    out.append(_linha("acoes_acompanhamento", "acoes", nivel,
                      f"{len(sem)} ação(ões) exigíveis sem acompanhamento no ciclo {hoje.year}-S{1 if hoje.month <= 6 else 2}"
                      if len(sem) else "Acompanhamento do ciclo completo",
                      [f"{r}: {n}" for r, n in resp.items()],
                      "Lembrar os responsáveis de preencher o formulário até o fim do semestre." if len(sem) else ""))
    return out


def metas(hoje: date) -> list[dict]:
    cat = pd.read_csv(config.REF_DIR / "indicadores_pls.csv", sep=";", dtype=str, keep_default_na=False)
    inf = cat[cat["automacao"] == "informado"]
    met = load_processed("pls_metas")
    ano = hoje.year - 1
    com_valor = set(met.loc[met["ano"] == ano, "indicador_id"]) if not met.empty else set()
    falta = [f"{r.id} · {r.responsavel}" for r in inf.itertuples() if r.id not in com_valor]
    return [_linha("metas_informados", "metas", "info" if falta else "ok",
                   f"{len(falta)} indicador(es) informados sem valor de {ano}" if falta else f"Informados de {ano} completos",
                   falta, "Lançar pelo formulário de valores informados." if falta else "")]


def verificar(hoje: date | None = None, falhas: dict[str, str] | None = None) -> pd.DataFrame:
    hoje = hoje or date.today()
    linhas = [_linha("modulo_falhou", m, "erro", f"Módulo {m} falhou na carga", [erro],
                     "Ver o log da carga (journalctl -u etl-pls-mensal).") for m, erro in (falhas or {}).items()]
    for f in (despesas, faturas, anomalias, compras, itens_quantidade, evg, comunidade_ufpb, inep, ipca, cnpj, acoes, metas):
        try:
            linhas += f(hoje)
        except Exception as e:  # verificacao quebrada nao derruba as outras
            linhas.append(_linha(f"verificacao_{f.__name__}", f.__name__, "erro", f"Verificação de {f.__name__} falhou",
                                 [f"{type(e).__name__}: {e}"]))
    try:
        linhas += gee()
    except Exception as e:
        linhas.append(_linha("verificacao_gee", "indicadores", "erro", "Verificação do GEE falhou", [str(e)]))
    df = pd.DataFrame(linhas)
    df["execucao"] = datetime.now().isoformat(timespec="seconds")
    df["data_referencia"] = hoje.isoformat()
    df["ordem"] = df["nivel"].map({n: i for i, n in enumerate(NIVEIS)})
    return df.sort_values(["ordem", "modulo"]).drop(columns="ordem").reset_index(drop=True)


# ---------------------------------------------------------------- alerta

def texto_alerta(df: pd.DataFrame) -> str:
    partes = [f"Carga mensal do Painel PLS UFPB — {df['execucao'].iloc[0]}", ""]
    for r in df[df["nivel"].isin(["erro", "atencao"])].itertuples():
        partes.append(f"[{r.nivel.upper()}] {r.titulo}")
        partes += [f"   - {d}" for d in r.detalhe[:10]]
        if r.acao_sugerida:
            partes.append(f"   O que fazer: {r.acao_sugerida}")
        partes.append("")
    url = os.environ.get("PAINEL_URL")
    if url:
        partes.append(f"Detalhes: {url.rstrip('/')}/pls/saude")
    return "\n".join(partes)


def enviar_alerta(df: pd.DataFrame) -> bool:
    problemas = df[df["nivel"].isin(["erro", "atencao"])]
    destinos = [e.strip() for e in os.environ.get("ALERTA_EMAILS", "").split(",") if e.strip()]
    host = os.environ.get("SMTP_HOST")
    if problemas.empty or not destinos or not host:
        return False
    msg = EmailMessage()
    n_erro = int((problemas["nivel"] == "erro").sum())
    msg["Subject"] = (f"[Painel PLS] carga com {n_erro} erro(s) e {len(problemas) - n_erro} ponto(s) de atenção")
    msg["From"] = os.environ.get("SMTP_REMETENTE", os.environ.get("SMTP_USUARIO", "painel-pls@localhost"))
    msg["To"] = ", ".join(destinos)
    msg.set_content(texto_alerta(df))
    porta = int(os.environ.get("SMTP_PORTA", "587"))
    with smtplib.SMTP(host, porta, timeout=60) as s:
        if os.environ.get("SMTP_TLS", "1") == "1":
            s.starttls()
        if os.environ.get("SMTP_USUARIO"):
            s.login(os.environ["SMTP_USUARIO"], os.environ.get("SMTP_SENHA", ""))
        s.send_message(msg)
    return True


def run(*, dry_run: bool = False, falhas: dict[str, str] | None = None, **_: object) -> pd.DataFrame:
    df = verificar(falhas=falhas)
    for r in df.itertuples():
        print(f"  [{r.nivel:>7}] {r.titulo}")
    if not dry_run:
        save_processed(df, COLLECTION, replace_on="execucao")
        if enviar_alerta(df):
            print("  alerta enviado por e-mail")
    replace_by(COLLECTION, df, "execucao", dry_run=dry_run)
    return df


if __name__ == "__main__":
    run()
