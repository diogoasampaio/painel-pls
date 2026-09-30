"""Consumo fisico das faturas de energia (kWh), agua (m3) e combustivel
(litros) -> pls_faturas.

Cadeia, toda com dado publico:
  1. pagamentos de energia (33903943) e agua (33903944) nos arquivos
     diarios do Portal ja em cache (data/raw/portal_bulk/) -> numero do
     processo, campus e numero da fatura (texto da observacao);
  2. consulta publica de processos do SIPAC -> documento FATURA (PDF);
  3. leitura do PDF (faturas/leitores.py) -> kWh ou m3 por unidade
     consumidora (UC) e mes de referencia; combustivel (33903001): relatorio
     de abastecimentos da gerenciadora de frota (faturas/combustivel.py),
     um registro por abastecimento, sem dado pessoal do condutor.

Um processo = uma fatura agrupada de um campus num mes. O resultado de
cada processo fica em data/raw/sipac/<ano>/<processo>.json e nao e
consultado de novo; o PDF e apagado depois de lido (SIPAC_GUARDAR_PDF=1
para manter). Processo sem fatura legivel fica registrado com o motivo e
e tentado de novo so com --refazer.

pls_faturas  1 doc por (processo, UC): periodo (mes de REFERENCIA do
             consumo, nao do pagamento), tipo, campus, ug, processo,
             fatura, uc, kwh_medido/kwh_faturado ou m3_medido/m3_faturado,
             demanda_kw, valor_bruto.
Chave de substituicao: processo.
"""

from __future__ import annotations

import re

import pandas as pd

from common import config
from common.mongo import replace_by
from common.periodo import Janela
from common.storage import raw_path, read_json, save_processed, write_json
from common.validation import report_counts
from faturas import processos_ufpb
from faturas.leitores import LEITORES
from faturas.sipac import Sipac

COLLECTION = "pls_faturas"
NATUREZAS = {"33903943": "energia", "33903944": "agua", "33903001": "combustivel", "33903978": "residuos"}
# natureza generica (33903978 e limpeza e conservacao): so os processos do fornecedor
FAVORECIDO = {"residuos": "GREEN|STERICYCLE"}
# especies em que o documento com o consumo aparece, em ordem de preferencia
ESPECIES = {
    # ago/2025 (energia): a fatura veio como ANEXO
    "energia": ("FATURA", "NOTA FISCAL", "DOCUMENTO COMPROBAT", "ANEXO", "PLANILHA", "TABELA", "DOCUMENTO"),
    "agua": ("FATURA", "NOTA FISCAL", "DOCUMENTO COMPROBAT", "ANEXO", "PLANILHA", "TABELA", "DOCUMENTO"),
    # o processo da gerenciadora tem varios relatorios (fiscalizacao por campus);
    # o de abastecimentos se chama RelatorioFaturamento...pdf
    # ate mai/2024 (GOLDI) o extrato com litros e a FATURA
    # jun-ago/2024 (PRIME) sem relatorio de abastecimentos: a NOTA (NF de servico) traz os litros do mes
    "combustivel": ("RELATÓRIO", "RELATORIO", "FATURA", "DOCUMENTO COMPROBAT", "PLANILHA", "NOTA"),
    # residuos de saude (B-Green/Stericycle): relatorio de fiscalizacao mensal da GMA/SINFRA, kg por campus
    "residuos": ("RELATÓRIO", "RELATORIO", "PLANILHA", "DOCUMENTO COMPROBAT", "ANEXO"),
}
NOME_PREFERIDO = {"combustivel": ("faturamento", "abastec", "faturas_goldi", "relatorio_prime", "relatrio_combust")}
# Subunidade do abastecimento -> campus. Os centros de fora de Joao Pessoa sao
# CCA (II), CCHSA (III) e CCAE (IV); o resto (CAMPUS1, SULT, CE, CT, PROEX,
# PROGEP... -- a GOLDI usa o departamento do empenho) e Campus I.
CAMPUS_FORA_JP = {"CCA": "II", "CCHSA": "III", "CCAE": "IV"}


def campus_subunidade(sub: object) -> str | None:
    if not isinstance(sub, str) or not sub:
        return None
    s = re.sub(r"\s", "", sub.upper())
    if s in CAMPUS_FORA_JP:
        return CAMPUS_FORA_JP[s]
    m = re.fullmatch(r"CAMPUS([1-4])", s)
    return ("I", "II", "III", "IV")[int(m.group(1)) - 1] if m else "I"
# processo de 33903001 que nao e da gerenciadora de frota (compra de material)
FORA_ESCOPO = {"combustivel": re.compile(r"MATERIAL DE CONSUMO|REPASSE|\bTED\b")}
_CAMPUS = r"CAMPUS\s+(IV|III|II|I)\b"


def normalizar_processo(texto: str) -> str | None:
    """Numero do processo como o Portal grava -> 'NNNNNN/AAAA-DV'.

    Formatos vistos: '004049/2024-54', '23074.017294/2026-72',
    '009815/2026-51.' e, desde 2026, so digitos: '23074017371202630'
    (radical+numero+ano+DV) ou '027309202606' (numero+ano+DV). O DV tem 2
    digitos: '042864/2024-3752' (retencao de mai/2024) e o 042864/2024-37."""
    t = re.sub(r"^\s*23074\.", "", texto or "")
    m = re.search(r"(\d+/\d{4}-\d{2})", t)
    if m:
        return m.group(1)
    d = re.sub(r"\D", "", t)
    if len(d) == 17 and d.startswith("23074"):
        d = d[5:]
    if len(d) == 12 and d[6:8] == "20":
        return f"{d[:6]}/{d[6:10]}-{d[10:]}"
    return None


def _corrigidos() -> dict[str, str]:
    arq = config.REF_DIR / "processos_corrigidos.csv"
    if not arq.exists():
        return {}
    ref = pd.read_csv(arq, sep=";", dtype=str)
    return dict(zip(ref["processo_portal"], ref["processo_sipac"]))


def _br(v: object) -> float:
    s = str(v or "0").strip()
    return float(s.replace(".", "").replace(",", ".")) if s else 0.0


def _corrigir_pela_base(df: pd.DataFrame) -> None:
    """Numero com DV invalido (digitado errado no Portal): troca pelo unico processo da base aberta
    com o mesmo ano, o mesmo DV, o assunto do tipo e ate 2 digitos de diferenca. Sem candidato
    unico, fica como veio e os candidatos vao para a verificacao (saude)."""
    ruins = df.loc[~df["processo"].map(processos_ufpb.valido), ["processo", "natureza"]].drop_duplicates("processo")
    if ruins.empty:
        return
    b = processos_ufpb.base()
    for r in ruins.itertuples():
        certo, cands = processos_ufpb.corrigir(r.processo, NATUREZAS[r.natureza], b)
        linhas = df["processo"] == r.processo
        if certo:
            print(f"  processo {r.processo} -> {certo} (base de processos da UFPB)", flush=True)
            df.loc[linhas, ["processo", "correcao"]] = [certo, "automatica"]
        else:
            df.loc[linhas, "candidatos"] = ", ".join(cands) or "nenhum"


def processos(janela: Janela) -> pd.DataFrame:
    """Processos de pagamento de energia, agua, combustivel e residuos cujo pagamento caiu na janela."""
    pg, imp = [], []
    for dia in janela.dias():
        arq = config.RAW_DIR / "portal_bulk" / f"{dia:%Y}" / f"{dia:%Y-%m-%d}.json"
        if not arq.exists():
            continue
        dados = read_json(arq).get("dados", {})
        pg += dados.get("pagamento", [])
        imp += dados.get("pagamento_impactados", [])
    if not imp:
        return pd.DataFrame()
    imp = pd.DataFrame(imp)
    imp["natureza"] = imp["codigo_natureza_despesa_completa"].str.replace(r"\D", "", regex=True).str[-8:]
    imp = imp[imp["natureza"].isin(NATUREZAS)]
    imp["pago"] = imp["valor_pago_r"].map(_br) + imp["valor_restos_a_pagar_pagos_r"].map(_br)
    df = imp.merge(pd.DataFrame(pg)[["codigo_pagamento", "codigo_unidade_gestora", "processo", "observacao", "data_emissao", "favorecido"]],
                   on="codigo_pagamento")
    df["processo"] = df["processo"].map(normalizar_processo)
    # campo vazio ou invalido ('-8'): vale o numero citado na observacao ('PROCESSO 23074.054669/2026-38')
    citado = df["observacao"].fillna("").str.extract(r"PROCESSO\s*(?:N[ºO°.]*\s*)?(?:23074\.?)?(\d{6}/\d{4}-\d{2})")[0]
    df["processo"] = df["processo"].fillna(citado)
    df = df[df["processo"].notna()].copy()
    df["processo_portal"] = df["processo"]
    # erro de digitacao conferido no SIPAC (ref/processos_corrigidos.csv)
    manual = _corrigidos()
    df["correcao"] = df["processo"].map(lambda p: "manual" if p in manual else None)
    df["processo"] = df["processo"].replace(manual)
    df["candidatos"] = None
    for tipo, padrao in FAVORECIDO.items():
        do_tipo = df["natureza"].map(NATUREZAS) == tipo
        do_fornecedor = df.loc[do_tipo & df["favorecido"].fillna("").str.upper().str.contains(padrao), "processo"]
        df = df[~do_tipo | df["processo"].isin(do_fornecedor)]
    df = df.copy()
    _corrigir_pela_base(df)
    obs = df["observacao"].fillna("")
    # ressarcimento de energia/agua por terceiro (fornecedor do RU de Bananeiras devolve a energia
    # que usou: pagamento negativo na natureza de energia) nao tem fatura -- o consumo ja esta
    # nas faturas da Energisa/CAGEPA
    df["ressarcimento"] = obs.str.upper().str.contains("RESSARCIMENTO")
    df["campus"] = obs.str.extract(_CAMPUS)[0]
    df["fatura_portal"] = obs.str.extract(r"FATURA\s*(?:N[ºO°.]*\s*)?(\d{4,})")[0]
    return (df.groupby("processo")
              .agg(tipo=("natureza", lambda s: NATUREZAS[s.iloc[0]]), ug=("codigo_unidade_gestora", "first"),
                   campus=("campus", "first"), fatura_portal=("fatura_portal", "first"),
                   pago_portal=("pago", "sum"), data_pagamento=("data_emissao", "min"),
                   ressarcimento=("ressarcimento", "all"), processo_portal=("processo_portal", "first"),
                   correcao=("correcao", "first"), candidatos=("candidatos", "first"))
              .reset_index())


def _cache(processo: str):
    num, ano = re.match(r"(\d+)/(\d{4})", processo).groups()
    return raw_path("sipac", ano, f"{processo.replace('/', '_')}.json")


def _consultar(sip: Sipac, r) -> dict:
    """Busca o processo, baixa o 1o PDF que o leitor do tipo reconhece, le e apaga."""
    reg = {"processo": r.processo, "tipo": r.tipo}
    achou = sip.buscar(r.processo)
    if not achou:
        return {**reg, "status": "processo_nao_encontrado"}
    docs = sip.documentos(achou["id"])
    reg.update(id=achou["id"], assunto=achou["assunto"], documentos=[{k: d[k] for k in ("ordem", "especie")} for d in docs])
    if r.tipo in FORA_ESCOPO and FORA_ESCOPO[r.tipo].search(achou["assunto"].upper()):
        return {**reg, "status": "fora_escopo"}
    especies = ESPECIES[r.tipo]
    candidatos = sorted(
        (d for d in docs if d["arquivo"] and d["especie"].upper().startswith(especies)),
        key=lambda d: next(i for i, e in enumerate(especies) if d["especie"].upper().startswith(e)),
    )
    if r.tipo in NOME_PREFERIDO and len(candidatos) > 1:
        # varios relatorios: o nome do arquivo (HEAD, sem baixar) aponta o certo
        preferidos = NOME_PREFERIDO[r.tipo]
        nomes = {d["ordem"]: sip.nome_arquivo(d["arquivo"]).lower() for d in candidatos}
        candidatos.sort(key=lambda d: not any(p in nomes[d["ordem"]] for p in preferidos))
    for d in candidatos:
        pdf = raw_path("sipac", "pdf", f"{r.processo.replace('/', '_')}_{d['ordem']}.pdf")
        try:
            sip.baixar(d["arquivo"], pdf)
            lido = LEITORES[r.tipo](pdf)
        except Exception as e:  # PDF corrompido ou fora do padrao: tenta o proximo documento
            print(f"  {r.processo} doc {d['ordem']}: {type(e).__name__}: {e}", flush=True)
            lido = None
        finally:
            if pdf.exists() and not config.SIPAC_GUARDAR_PDF:
                pdf.unlink()
        if lido and lido["unidades"]:
            return {**reg, "status": "ok", "documento": d["ordem"], **lido}
    return {**reg, "status": "sem_fatura_legivel"}


# R$/kWh plausivel (tarifa verde/azul + impostos): fora disso, a leitura do PDF errou
TARIFA_KWH = (0.25, 4.0)


def suspeito(res: dict) -> bool:
    """Fatura de energia lida com kWh implausivel para o valor: e consultada de
    novo com --refazer (o PDF nao fica guardado)."""
    if res.get("tipo") != "energia":
        return False
    for u in res.get("unidades", []):
        kwh = u.get("kwh_medido") or u.get("kwh_faturado")
        valor = u.get("valor_bruto")
        if kwh is None or (u.get("kwh_medido") and u.get("kwh_faturado") and u["kwh_medido"] > u["kwh_faturado"] * 1.05):
            return True
        # UC pequena (ate R$ 200) tem taxa minima e CIP: nao da para julgar pela tarifa
        if valor and valor > 200 and kwh > 0 and not TARIFA_KWH[0] <= valor / kwh <= TARIFA_KWH[1]:
            return True
    return False


def extract(janela: Janela, *, refazer: bool = False, offline: bool = False) -> tuple[pd.DataFrame, dict]:
    procs = processos(janela)
    info = {"processos": len(procs), "do_cache": 0, "consultados": 0}
    if procs.empty:
        return pd.DataFrame(), info
    sip = None
    resultados = []
    for i, r in enumerate(procs.itertuples(), 1):
        if r.ressarcimento:
            resultados.append((r, {"processo": r.processo, "tipo": r.tipo, "status": "fora_escopo",
                                   "motivo": "ressarcimento de terceiro, sem fatura"}))
            continue
        path = _cache(r.processo)
        res = read_json(path) if path.exists() else None
        if res and ((res["status"] == "ok" and not suspeito(res)) or not refazer):
            info["do_cache"] += 1
        elif offline:
            continue
        else:
            sip = sip or Sipac()
            try:
                res = _consultar(sip, r)
            except Exception as e:  # rede/servidor: registra e segue; a proxima execucao tenta de novo
                print(f"  {r.processo}: falha na consulta ({type(e).__name__}: {e})", flush=True)
                continue
            write_json(path, res)
            info["consultados"] += 1
            if info["consultados"] % 10 == 0:
                print(f"  {i}/{len(procs)} processos ({info['consultados']} consultados no SIPAC)", flush=True)
        resultados.append((r, res))
    return _transform(resultados), info


def _transform(resultados: list) -> pd.DataFrame:
    linhas = []
    for r, res in resultados:
        # desde 2026 a observacao do Portal nao traz o campus; o assunto do processo traz
        campus = r.campus if isinstance(r.campus, str) else None
        if not campus:
            m = re.search(_CAMPUS, (res.get("assunto") or "").upper())
            campus = m.group(1) if m else None
        base = {
            "processo": r.processo, "tipo": r.tipo, "ug": r.ug, "campus": campus,
            "fatura_portal": r.fatura_portal, "pago_portal_processo": r.pago_portal, "data_pagamento": r.data_pagamento,
            "status": res["status"], "fatura": res.get("fatura"), "id_sipac": res.get("id"),
            "valor_bruto_fatura": res.get("valor_bruto"),  # CAGEPA: total da fatura agrupada
            "assunto_sipac": res.get("assunto"),
            "processo_portal": r.processo_portal, "correcao": r.correcao, "candidatos": r.candidatos,
        }
        if res["status"] != "ok":
            linhas.append(base)
            continue
        for u in res["unidades"]:
            linhas.append({**base, **{k: u.get(k) for k in (
                "uc", "nome", "referencia", "kwh_faturado", "kwh_medido", "demanda_kw",
                "m3_medido", "m3_faturado", "valor", "valor_bruto",
                "transacao", "data", "subunidade", "placa", "combustivel", "combustivel_texto", "litros", "preco_litro",
                "cnpj_posto", "kg")}})
    df = pd.DataFrame(linhas)
    if df.empty:
        return df
    resid = df["tipo"] == "residuos"
    if resid.any():
        # um processo cobre os quatro campi: campus pela linha da medicao
        df.loc[resid, "campus"] = df.loc[resid, "uc"].str.extract(_CAMPUS, expand=False)
        # a planilha de medicao as vezes repete o periodo do mes anterior; o assunto
        # do processo ('SERVICOS PRESTADOS NO PERIODO DE 01/02/2026 A ...') e o confiavel
        mes = df.loc[resid, "assunto_sipac"].fillna("").str.upper().str.extract(r"PER.ODO DE \d{2}/(\d{2})/(\d{4})")
        df.loc[resid, "referencia"] = (mes[1] + "-" + mes[0]).fillna(df.loc[resid, "referencia"])
    comb = df["tipo"] == "combustivel"
    if comb.any():
        # abastecimento: mes da propria transacao; campus pela subunidade
        df.loc[comb, "referencia"] = df.loc[comb, "data"].str[:7]
        df.loc[comb, "campus"] = df.loc[comb, "subunidade"].map(campus_subunidade)
        # o mesmo relatorio pode estar anexado a mais de um processo (uma UG paga, a outra retem tributo)
        # linha de taxa/servico zerada do extrato GOLDI (cache anterior ao filtro no leitor)
        df = df[~(comb & (df["valor_bruto"] == 0))]
        comb = df["tipo"] == "combustivel"
        tem_transacao = comb & df["transacao"].notna()
        dup = tem_transacao & df.duplicated(["transacao", "data"], keep="first")
        # linhas da NF (sem transacao): a mesma NF anexada a dois processos conta uma vez
        nota = comb & df["transacao"].isna() & df["placa"].isna()
        dup |= nota & df.duplicated(["data", "combustivel_texto", "litros"], keep="first")
        df = df[~dup]
    df["periodo"] = df["referencia"]
    if "m3_medido" in df:
        # agua: vale o medido, salvo leitura anomala (troca de hidrometro: 72.055 m3
        # medidos e 263 faturados em jun/2024) -- ai vale o faturado
        anomalo = df["m3_faturado"].notna() & (df["m3_medido"] > 5 * df["m3_faturado"] + 100)
        df["m3"] = df["m3_medido"].where(~anomalo, df["m3_faturado"])
    if "kwh_medido" in df:
        # UC faturada pelo minimo/media: vale o medido (consumo real)
        df["kwh"] = df["kwh_medido"].fillna(df["kwh_faturado"])
    df["ano"] = pd.to_numeric(df["periodo"].str[:4], errors="coerce")
    return df


def run(*, dry_run: bool = False, inicio: str | None = None, fim: str | None = None, offline: bool = False,
        refazer: bool = False, **_: object) -> None:
    janela = Janela.de_args(inicio, fim)
    df, info = extract(janela, refazer=refazer, offline=offline)
    report_counts("processos de energia, agua, combustivel e residuos", info)
    if df.empty:
        print("Faturas: nada na janela")
        return
    por_proc = df.drop_duplicates("processo")
    report_counts("processos por situacao", por_proc.groupby("status").size().to_dict())
    ok = df[df["status"] == "ok"]
    if not ok.empty:
        e = ok[ok["tipo"] == "energia"].groupby("ano")["kwh"].sum().astype(float).round(0) if "kwh" in ok else pd.Series(dtype=float)
        a = ok[ok["tipo"] == "agua"].groupby("ano")["m3"].sum().astype(float).round(0) if "m3" in ok else pd.Series(dtype=float)
        r = ok[ok["tipo"] == "residuos"].groupby("ano")["kg"].sum().astype(float).round(0) if "kg" in ok else pd.Series(dtype=float)
        c = ok[ok["tipo"] == "combustivel"].groupby("ano")["litros"].sum().astype(float).round(0) if "litros" in ok else pd.Series(dtype=float)
        report_counts("kWh por ano de referencia", {str(int(k)): float(v) for k, v in e.items()})
        report_counts("m3 por ano de referencia", {str(int(k)): float(v) for k, v in a.items()})
        report_counts("kg de residuos por ano de referencia", {str(int(k)): float(v) for k, v in r.items()})
        report_counts("litros de combustivel por ano de referencia", {str(int(k)): float(v) for k, v in c.items()})
    falhas = por_proc[por_proc["status"] != "ok"]
    if not falhas.empty:
        print(f"  processos sem leitura ({len(falhas)}):")
        print(falhas[["processo", "tipo", "campus", "status"]].head(15).to_string(index=False))
    if not dry_run:
        save_processed(df, COLLECTION, replace_on="processo")
    replace_by(COLLECTION, df, "processo", dry_run=dry_run)


if __name__ == "__main__":
    run()
