"""Contratacoes da UFPB no PNCP (Lei 14.133) -> N10, N11 e marcadores dos editais.

Fontes (todas publicas, sem login):
  Compras.gov.br dados abertos  modulo-contratacoes/1_consultarContratacoes_PNCP_14133
                                (lista das contratacoes por CNPJ e modalidade)
                                modulo-arp (atas de registro de precos da UFPB,
                                unidades participantes e adesoes por item)
  PNCP                          /api/pncp/v1/orgaos/{cnpj}/compras/{ano}/{seq}/arquivos
                                e /itens (documentos e itens de cada compra);
                                /api/consulta/v1/contratos (contratos e empenhos da
                                UFPB com a compra de origem e o flag frutoAdesao)

O PNCP devolve 429 com poucas dezenas de chamadas seguidas: cliente a
PNCP_RPM por minuto e espera de 60 s no 429 (common.http).

Cache em data/raw/compras/:
  contratacoes_<ano>.json         lista do ano (ano fechado ha mais de 90 dias nao e rebaixado)
  contratos_<ano>.json            contratos/empenhos publicados no ano
  docs/<controle>.json.gz         texto de cada pagina dos documentos + itens da compra
                                  (rebaixado so se a compra foi atualizada no PNCP)
  arp/<uasg>_<ata>.json           unidades e adesoes de cada ata (fechada quando a vigencia acaba)

A classificacao (compras.classificar) roda sempre sobre o texto em cache:
mudar ref/criterios_editais.csv nao exige baixar nada de novo.

Colecoes:
  pls_compras               1 doc por contratacao: modalidade, SRP, objeto, valor,
                            nivel de sustentabilidade (especifico | preferencial |
                            generico | nenhum | sem_texto | nao_lido), criterios e trechos,
                            marcadores (mao de obra exclusiva, cota para mulheres,
                            mao de obra local, alimentos, agricultura familiar,
                            obra, BIM) e margem de preferencia (itens do PNCP)
  pls_compras_compartilhadas 1 doc por compra compartilhada: IRP da UFPB com
                            participante externo, ata da UFPB com adesao externa,
                            compra de outro orgao usada pela UFPB (participacao ou adesao)
"""

from __future__ import annotations

import gzip
import json
import re
from datetime import date, datetime

import pandas as pd
import requests

from common import config
from common.http import HttpClient
from common.mongo import replace_by
from common.periodo import Janela
from common.storage import raw_path, read_json, save_processed, write_json
from common.validation import report_counts
from compras.classificar import TIPO_ESTUDO, TIPOS_REQUISITO, classificar, paginas

COL_COMPRAS = "pls_compras"
COL_COMPARTILHADAS = "pls_compras_compartilhadas"

COMPRAS_API = "https://dadosabertos.compras.gov.br"
PNCP_API = "https://pncp.gov.br/api/pncp/v1"
PNCP_CONSULTA = "https://pncp.gov.br/api/consulta/v1"
CNPJ_UFPB = "24098477000110"
MODALIDADES = range(1, 15)  # codigos do Compras.gov.br; os vazios so custam uma chamada
SEM_DOCUMENTOS = re.compile(r"^INEXIGIBILIDADE", re.I)  # assinaturas, cursos, credenciamento: sem TR
DIAS_FECHADO = 90
PNCP_RPM = 20
COMPRAS_RPM = 50


def _pncp() -> HttpClient:
    return HttpClient(per_minute=PNCP_RPM, timeout=180)


def _compras() -> HttpClient:
    return HttpClient(per_minute=COMPRAS_RPM, timeout=120)


def _fechado(ano: int, hoje: date) -> bool:
    return (hoje - date(ano, 12, 31)).days > DIAS_FECHADO


def _paginar_compras(cli: HttpClient, rota: str, params: dict) -> list[dict]:
    """O Compras.gov.br responde 404 ("Resource not found") para consulta sem registros em alguns
    itens de ata: tratado como lista vazia."""
    out, pagina = [], 1
    while True:
        try:
            d = cli.get_json(f"{COMPRAS_API}/{rota}", {**params, "pagina": pagina, "tamanhoPagina": 500}) or {}
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                return out
            raise
        out += d.get("resultado") or []
        if not d.get("paginasRestantes"):
            return out
        pagina += 1


# ---------------------------------------------------------------- contratacoes

def contratacoes(ano: int, hoje: date, cli: HttpClient) -> list[dict]:
    arq = raw_path("compras", f"contratacoes_{ano}.json")
    if arq.exists() and _fechado(ano, hoje):
        return read_json(arq)
    regs = []
    for m in MODALIDADES:
        regs += _paginar_compras(cli, "modulo-contratacoes/1_consultarContratacoes_PNCP_14133", {
            "orgaoEntidadeCnpj": CNPJ_UFPB, "codigoModalidade": m,
            "dataPublicacaoPncpInicial": f"{ano}-01-01", "dataPublicacaoPncpFinal": f"{ano}-12-31"})
    regs = [r for r in regs if not r.get("contratacaoExcluida")]
    write_json(arq, regs)
    return regs


def _chave(controle: str) -> tuple[str, int, int]:
    """'24098477000110-1-000370/2024' -> (cnpj, ano, sequencial)"""
    m = re.fullmatch(r"(\d{14})-\d+-(\d+)/(\d{4})", controle)
    return m.group(1), int(m.group(3)), int(m.group(2))


def _arquivo_docs(controle: str):
    return raw_path("compras", "docs", re.sub(r"\W", "_", controle) + ".json.gz")


def documentos(compra: dict, cli: HttpClient) -> dict:
    """Texto dos documentos e itens da compra, com cache pela data de atualizacao."""
    controle = compra["numeroControlePNCP"]
    arq = _arquivo_docs(controle)
    atualizado = compra.get("dataAtualizacaoPncp") or ""
    if arq.exists():
        cache = json.loads(gzip.decompress(arq.read_bytes()))
        if cache.get("atualizado") == atualizado:
            return cache
    cnpj, ano, seq = _chave(controle)
    base = f"{PNCP_API}/orgaos/{cnpj}/compras/{ano}/{seq}"
    arquivos = cli.get_json(f"{base}/arquivos") or []
    docs = []
    for a in arquivos:
        tipo = a.get("tipoDocumentoNome") or ""
        if not a.get("statusAtivo", True) or (tipo not in TIPOS_REQUISITO and tipo != TIPO_ESTUDO):
            continue
        resp = cli.get(a["url"])
        nome = re.search(r'filename="?([^";]+)', resp.headers.get("content-disposition", "")) or None
        docs.append({"tipo": tipo, "titulo": a.get("titulo"), "sequencial": a.get("sequencialDocumento"),
                     "paginas": paginas(resp.content, nome.group(1) if nome else "")})
    itens = cli.get_json(f"{base}/itens", {"pagina": 1, "tamanhoPagina": 1000}) or []
    cache = {
        "atualizado": atualizado, "baixado_em": datetime.now().isoformat(timespec="seconds"),
        "tipos_publicados": sorted({a.get("tipoDocumentoNome") or "" for a in arquivos}), "docs": docs,
        "itens": [{k: i.get(k) for k in ("numeroItem", "materialOuServico", "tipoBeneficioNome", "valorTotal",
                                          "aplicabilidadeMargemPreferenciaNormal",
                                          "aplicabilidadeMargemPreferenciaAdicional", "catalogoCodigoItem")}
                  for i in itens],
    }
    arq.parent.mkdir(parents=True, exist_ok=True)
    arq.write_bytes(gzip.compress(json.dumps(cache, ensure_ascii=False).encode()))
    return cache


def _linha_compra(c: dict, cache: dict | None, leitura: str) -> dict:
    homologado = c.get("valorTotalHomologado") or 0.0
    estimado = c.get("valorTotalEstimado") or 0.0
    data = (c.get("dataPublicacaoPncp") or "")[:10]
    base = {
        "controle": c["numeroControlePNCP"], "id_compra": c.get("idCompra"), "ug": c.get("unidadeOrgaoCodigoUnidade"),
        "data_publicacao": data, "periodo": data[:7], "ano": int(data[:4]) if data else None,
        "modalidade": c.get("modalidadeNome"), "srp": bool(c.get("srp")), "processo": c.get("processo"),
        "objeto": c.get("objetoCompra"), "amparo": c.get("amparoLegalNome"), "situacao": c.get("situacaoCompraNomePncp"),
        "valor_estimado": estimado, "valor_homologado": homologado,
        "valor": homologado if homologado > 0 else estimado, "leitura": leitura,
    }
    docs = [(d["tipo"], d["paginas"]) for d in (cache or {}).get("docs", [])]
    cl = classificar(docs, c.get("objetoCompra") or "")
    if leitura != "lido":
        cl["nivel_sustentabilidade"] = leitura
    elif not docs:
        cl["nivel_sustentabilidade"] = "sem_documento"
    itens = (cache or {}).get("itens", [])
    return {**base, **{k: cl[k] for k in ("nivel_sustentabilidade", "criterios", "preferenciais", "genericos", "marcadores", "trechos")},
            "documentos_lidos": [d["tipo"] for d in (cache or {}).get("docs", [])],
            "tipos_publicados": (cache or {}).get("tipos_publicados", []),
            "n_itens": len(itens),
            "margem_preferencia": any(i.get("aplicabilidadeMargemPreferenciaNormal")
                                      or i.get("aplicabilidadeMargemPreferenciaAdicional") for i in itens),
            "itens_exclusivos_me_epp": sum(1 for i in itens if "exclusiva" in (i.get("tipoBeneficioNome") or "").lower())}


# ---------------------------------------------------------------- compras compartilhadas

def contratos(ano: int, hoje: date, cli: HttpClient) -> list[dict]:
    arq = raw_path("compras", f"contratos_{ano}.json")
    if arq.exists() and _fechado(ano, hoje):
        return read_json(arq)
    out, pagina = [], 1
    while True:
        d = cli.get_json(f"{PNCP_CONSULTA}/contratos", {
            "dataInicial": f"{ano}0101", "dataFinal": f"{ano}1231", "cnpjOrgao": CNPJ_UFPB,
            "pagina": pagina, "tamanhoPagina": 500}) or {}
        out += [{k: r.get(k) for k in ("numeroControlePNCP", "numeroControlePncpCompra", "numeroControlePncpAta",
                                        "frutoAdesao", "objetoContrato", "valorGlobal", "dataAssinatura",
                                        "dataPublicacaoPncp", "nomeRazaoSocialFornecedor")} for r in d.get("data") or []]
        if not d.get("paginasRestantes"):
            break
        pagina += 1
    write_json(arq, out)
    return out


def compras_externas(regs: list[dict]) -> list[dict]:
    """Contratos/empenhos da UFPB cuja compra de origem e de outro orgao, 1 por compra."""
    vistos: dict[str, dict] = {}
    for r in sorted(regs, key=lambda r: r.get("dataAssinatura") or ""):
        compra = r.get("numeroControlePncpCompra") or ""
        if not compra or compra.startswith(CNPJ_UFPB):
            continue
        d = (r.get("dataAssinatura") or r.get("dataPublicacaoPncp") or "")[:10]
        atual = vistos.setdefault(compra, {
            "tipo": "Adesão da UFPB a ata de outro órgão" if r.get("frutoAdesao") else "Participação da UFPB em compra de outro órgão",
            "referencia": compra, "orgao_cnpj": compra[:14], "data": d, "detalhe": (r.get("objetoContrato") or "")[:200],
            "valor": 0.0})
        atual["valor"] += r.get("valorGlobal") or 0.0
        if r.get("frutoAdesao"):
            atual["tipo"] = "Adesão da UFPB a ata de outro órgão"
    return list(vistos.values())


def _uasgs_ufpb() -> set[str]:
    return set(config.UGS)


def atas(ano: int, cli: HttpClient) -> list[dict]:
    """Itens das atas de registro de precos das UASGs da UFPB com vigencia iniciada no ano."""
    out = []
    for uasg in config.UGS:
        out += _paginar_compras(cli, "modulo-arp/2_consultarARPItem", {
            "codigoUnidadeGerenciadora": uasg, "dataVigenciaInicialMin": f"{ano}-01-01",
            "dataVigenciaInicialMax": f"{ano}-12-31"})
    return [r for r in out if not r.get("itemExcluido")]


def compartilhamento_ata(uasg: str, numero_ata: str, itens: list[str], vigencia_fim: str, hoje: date,
                         cli: HttpClient) -> dict:
    """Participantes externos e adesoes externas de uma ata (para no primeiro achado de cada)."""
    arq = raw_path("compras", "arp", f"{uasg}_{numero_ata.replace('/', '-')}.json")
    if arq.exists():
        cache = read_json(arq)
        if cache.get("fechado") or (hoje - date.fromisoformat(cache["consultado_em"])).days < 30:
            return cache
    ufpb = _uasgs_ufpb()
    participantes: set[str] = set()
    adesoes: list[dict] = []
    for item in sorted({str(i) for i in itens if i}):
        params = {"numeroAta": numero_ata, "unidadeGerenciadora": uasg, "numeroItem": item}
        unidades = _paginar_compras(cli, "modulo-arp/3_consultarUnidadesItem", params)
        for u in unidades:
            if u.get("tipoUnidade") == "PARTICIPANTE" and u.get("codigoUnidade") not in ufpb:
                participantes.add(f"{u.get('codigoUnidade')} - {u.get('nomeUnidade')}")
        houve_adesao = any((u.get("qtdLimiteAdesao") or 0) > (u.get("saldoAdesoes") or 0) for u in unidades
                           if u.get("aceitaAdesao"))
        if houve_adesao and not adesoes:
            for a in _paginar_compras(cli, "modulo-arp/5_consultarAdesoesItem", params):
                unidade = a.get("unidadeNaoParticipante") or ""
                if unidade[:6] not in ufpb:
                    adesoes.append({"unidade": unidade, "data": (a.get("dataAprovacaoAnalise") or "")[:10]})
        if participantes and adesoes:
            break
    cache = {"uasg": uasg, "ata": numero_ata, "participantes": sorted(participantes), "adesoes": adesoes,
             "consultado_em": hoje.isoformat(), "fechado": bool(vigencia_fim) and vigencia_fim < hoje.isoformat()}
    write_json(arq, cache)
    return cache


def compartilhadas_ufpb(ano: int, hoje: date, cli: HttpClient) -> list[dict]:
    itens = atas(ano, cli)
    por_ata: dict[tuple[str, str], dict] = {}
    for r in itens:
        if not r.get("numeroAtaRegistroPreco") or not r.get("numeroItem"):
            continue  # ata ainda sem numero (em assinatura)
        k = (str(r["codigoUnidadeGerenciadora"]), str(r["numeroAtaRegistroPreco"]))
        a = por_ata.setdefault(k, {"itens": [], "assinatura": (r.get("dataAssinatura") or "")[:10],
                                   "fim": r.get("dataVigenciaFinal") or "", "compra": r.get("numeroControlePncpCompra"),
                                   "objeto": r.get("descricaoItem")})
        a["itens"].append(r["numeroItem"])
    out = []
    for (uasg, ata), a in sorted(por_ata.items()):
        c = compartilhamento_ata(uasg, ata, a["itens"], a["fim"], hoje, cli)
        ref = f"UASG {uasg} · ARP {ata}"
        if c["participantes"]:
            out.append({"tipo": "IRP da UFPB com participante externo", "referencia": ref, "compra": a["compra"],
                        "data": a["assinatura"], "detalhe": "; ".join(c["participantes"])[:300], "valor": None})
        if c["adesoes"]:
            primeira = min((x["data"] for x in c["adesoes"] if x["data"]), default=a["assinatura"])
            out.append({"tipo": "Ata da UFPB com adesão de outro órgão", "referencia": ref, "compra": a["compra"],
                        "data": primeira, "detalhe": "; ".join(sorted({x["unidade"] for x in c["adesoes"]}))[:300],
                        "valor": None})
    return out


# ---------------------------------------------------------------- run

def run(*, dry_run: bool = False, inicio: str | None = None, fim: str | None = None, offline: bool = False,
        refazer: bool = False, **_: object) -> None:
    hoje = date.today()
    janela = Janela.de_args(inicio or "2023-01", fim)
    anos = janela.anos()
    pncp, compras_cli = _pncp(), _compras()
    linhas, compartilhadas, erros = [], [], []
    for ano in anos:
        lista = read_json(raw_path("compras", f"contratacoes_{ano}.json")) if offline else contratacoes(ano, hoje, compras_cli)
        print(f"Compras {ano}: {len(lista)} contratacoes no PNCP", flush=True)
        for i, c in enumerate(lista, 1):
            leitura, cache = "lido", None
            if SEM_DOCUMENTOS.match(c.get("modalidadeNome") or ""):
                leitura = "nao_lido"
            else:
                try:
                    arq = _arquivo_docs(c["numeroControlePNCP"])
                    if offline or (arq.exists() and not refazer and _fechado(ano, hoje)):
                        cache = json.loads(gzip.decompress(arq.read_bytes())) if arq.exists() else None
                    else:
                        cache = documentos(c, pncp)
                except Exception as e:  # PNCP fora do ar ou documento corrompido: tenta de novo na proxima
                    erros.append(f"{c['numeroControlePNCP']}: {type(e).__name__}: {e}")
                    leitura = "erro"
            linhas.append(_linha_compra(c, cache, leitura))
            if i % 25 == 0:
                print(f"  {i}/{len(lista)} ({pncp.calls} chamadas ao PNCP)", flush=True)
        if not offline:
            try:
                for x in compras_externas(contratos(ano, hoje, pncp)):
                    compartilhadas.append(x)
                compartilhadas += compartilhadas_ufpb(ano, hoje, compras_cli)
            except Exception as e:
                erros.append(f"compras compartilhadas {ano}: {type(e).__name__}: {e}")
    df = pd.DataFrame(linhas)
    if df.empty:
        print("Compras: nenhuma contratacao na janela")
        return
    report_counts("contratacoes por ano e modalidade",
                  {f"{a} {m}": n for (a, m), n in df.groupby(["ano", "modalidade"]).size().items()})
    report_counts("nivel de sustentabilidade", df.groupby("nivel_sustentabilidade").size().to_dict())
    comp = pd.DataFrame(compartilhadas)
    if not comp.empty:
        comp = comp.drop_duplicates(["tipo", "referencia"])
        comp["periodo"] = comp["data"].str[:7]
        comp["ano"] = pd.to_numeric(comp["data"].str[:4], errors="coerce")
        report_counts("compras compartilhadas por tipo", comp.groupby("tipo").size().to_dict())
    if erros:
        print(f"  {len(erros)} erro(s) de leitura (tenta de novo na proxima carga):")
        for e in erros[:10]:
            print("   ", e)
    if not dry_run:
        save_processed(df, COL_COMPRAS, replace_on="ano")
        if not comp.empty:
            save_processed(comp, COL_COMPARTILHADAS, replace_on="ano")
    replace_by(COL_COMPRAS, df, "ano", dry_run=dry_run)
    if not comp.empty:
        replace_by(COL_COMPARTILHADAS, comp, "ano", dry_run=dry_run)


if __name__ == "__main__":
    run()
