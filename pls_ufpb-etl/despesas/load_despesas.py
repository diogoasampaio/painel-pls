"""Carga das despesas da UFPB (Portal da Transparencia) classificadas nos
temas do PLS.

Fontes, por dia da janela:
  1. arquivo diario de dados abertos (despesas/portal_bulk.py) -- historico
     e mes a mes; sem limite de requisicoes, natureza de 8 digitos pronta e
     quantidade/valor unitario do item em colunas;
  2. API (despesas/portal_api.py) -- so para os dias cujo arquivo ainda nao
     foi publicado (404), e so se houver PORTAL_API_KEY.
As duas fontes sao normalizadas no mesmo formato (_dia_bulk / _dia_api).

Colecoes:
  pls_despesas       fato: 1 documento por (documento de liquidacao ou
                     pagamento x empenho impactado x subitem), so de
                     naturezas relevantes ao PLS (folha etc. fica de fora).
                     Metrica em `valor`: liquidacao -> valor liquidado;
                     pagamento -> valor pago + restos a pagar pagos
                     (essencial para energia/agua que viram o ano).
  pls_empenhos       notas de empenho do periodo (natureza, favorecido).
  pls_itens_empenho  itens das NE originais de naturezas relevantes:
                     descricao, quantidade, valor unitario, regras de texto
                     (papel A4, copo descartavel, LED, fotovoltaica...).

Chave de substituicao: `periodo` (AAAA-MM da data do documento).

Por que liquidacao e nao empenho como consumo: energia e agua costumam
ter empenho estimativo anual lancado em janeiro; a liquidacao acompanha a
fatura do mes.

LGPD: favorecido pessoa fisica (diarias, ressarcimentos) tem CPF, nome e
observacao do documento suprimidos (a observacao costuma citar o servidor).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime

import pandas as pd

from common import config, pls_map
from common.mongo import replace_by
from common.periodo import Janela
from common.storage import read_json, save_processed
from common.text import parse_valor
from common.validation import load_expected_csv, report_counts
from despesas.portal_api import FASES, PortalApi
from despesas.portal_bulk import PortalBulk

COL_FATO = "pls_despesas"
COL_EMPENHOS = "pls_empenhos"
COL_ITENS = "pls_itens_empenho"

FASES_FATO = (2, 3)  # liquidacao, pagamento
VALIDACAO_TG = config.DATA_DIR / "validacao" / "tesouro_gerencial_liquidado.csv"


@dataclass
class Dia:
    empenhos: list[dict] = field(default_factory=list)
    itens: list[dict] = field(default_factory=list)
    fatos: list[dict] = field(default_factory=list)
    fonte: str = ""


# ---------------------------------------------------------------- helpers

def _data_iso(valor: str | None) -> str | None:
    if not valor:
        return None
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(valor[:10], fmt).date().isoformat()
        except ValueError:
            continue
    return None


def _tempo(data: str) -> dict:
    return {"periodo": data[:7], "ano": int(data[:4]), "mes": int(data[5:7]), "data": data}


def _pessoa_fisica(codigo: str | None) -> bool:
    c = str(codigo or "")
    return "*" in c or len(re.sub(r"\D", "", c)) == 11


def _favorecido(codigo: str | None, nome: str | None, observacao: str | None) -> dict:
    if _pessoa_fisica(codigo):
        return {"favorecido_tipo": "PF", "favorecido_codigo": None, "favorecido_nome": None, "observacao": None}
    return {
        "favorecido_tipo": "PJ" if len(re.sub(r"\D", "", str(codigo or ""))) == 14 else "outro",
        "favorecido_codigo": codigo,
        "favorecido_nome": nome,
        "observacao": observacao,
    }


def _classif(natureza: str | None) -> dict:
    c = pls_map.classificar_natureza(natureza)
    return {"tema_codigo": c.tema_codigo, "subtema": c.subtema, "natureza_mapeada": c.natureza_mapeada}


def _item(base: dict, empenho: str, natureza: str | None, descricao, **extra) -> dict:
    return {
        **base, "empenho": empenho, "natureza": natureza, "descricao": descricao,
        "regras_texto": [r["regra"] for r in pls_map.classificar_texto(descricao)],
        "quantidade_texto": pls_map.quantidade_no_texto(descricao),
        **extra, **_classif(natureza),
    }


def _fato(base: dict, fase: int, documento: str, especie, empenho, subitem, natureza, liq, pago, rp_pago, rp_insc, rp_canc, fav: dict) -> dict:
    return {
        **base, "fase": FASES[fase], "documento": documento, "especie": especie, "empenho": empenho,
        "subitem": subitem, "natureza": natureza,
        "valor": liq if fase == 2 else pago + rp_pago,
        "valor_liquidado": liq, "valor_pago": pago, "valor_rp_pago": rp_pago,
        "valor_rp_inscrito": rp_insc, "valor_rp_cancelado": rp_canc,
        **fav, **_classif(natureza),
    }


# ---------------------------------------------------------------- fonte 1: arquivos diarios

def _col(linha: dict, *prefixos: str):
    """Valor da primeira coluna cujo nome (snake) comeca com um dos prefixos --
    os nomes do CSV variam ('..._r', '..._convertido_pra_r')."""
    for p in prefixos:
        for k, v in linha.items():
            if k == p or k.startswith(p):
                return v
    return None


def _exigir(linhas: list[dict], arquivo: str, *colunas: str) -> None:
    if linhas:
        faltando = [c for c in colunas if not any(k.startswith(c) for k in linhas[0])]
        if faltando:
            raise KeyError(f"{arquivo}: colunas esperadas ausentes {faltando}; recebidas {list(linhas[0])}")


_PARTES = (("codigo_categoria_de_despesa", 1), ("codigo_grupo_de_despesa", 1),
           ("codigo_modalidade_de_aplicacao", 2), ("codigo_elemento_de_despesa", 2))


def _natureza_por_partes(linha: dict, com_subelemento: bool = False) -> str | None:
    partes = [*_PARTES, ("codigo_subelemento_de_despesa", 2)] if com_subelemento else list(_PARTES)
    valores = [re.sub(r"\D", "", str(_col(linha, c) or "")) for c, _ in partes]
    if not all(valores):
        return None
    return "".join(v.zfill(n) for v, (_, n) in zip(valores, partes))


def _nat8_completa(completa, subitem) -> str | None:
    d = re.sub(r"\D", "", str(completa or ""))
    if len(d) >= 8:
        return d[:8]
    if len(d) == 6:
        return pls_map.natureza8(d, subitem) or d
    return None


def _dia_bulk(bruto: dict[str, list[dict]], dia: date, acoes: dict[str, str] | None = None) -> Dia:
    """`acoes`: empenho -> acao orcamentaria (de todo o cache; o pagamento nao traz a acao)."""
    out = Dia(fonte="arquivo")
    _exigir(bruto["empenho"], "Empenho", "codigo_empenho", "data_emissao", "codigo_elemento_de_despesa")
    _exigir(bruto["item_empenho"], "ItemEmpenho", "codigo_empenho", "codigo_subelemento_de_despesa", "descricao")
    for arq, doc in (("liquidacao", "codigo_liquidacao"), ("pagamento", "codigo_pagamento")):
        _exigir(bruto[arq], arq, doc, "data_emissao", "codigo_favorecido")
        _exigir(bruto[f"{arq}_impactados"], f"{arq}_impactados", doc, "codigo_empenho", "codigo_natureza_despesa_completa")

    originais = {}
    for e in bruto["empenho"]:
        data = _data_iso(_col(e, "data_emissao")) or dia.isoformat()
        nat6 = _natureza_por_partes(e)
        especie = _col(e, "especie_empenho")
        out.empenhos.append({
            **_tempo(data), "ug": e.get("codigo_unidade_gestora"), "documento": e["codigo_empenho"],
            "especie": especie, "natureza6": nat6, "elemento": _col(e, "elemento_de_despesa"),
            "valor": parse_valor(_col(e, "valor_do_empenho_convertido", "valor_original_do_empenho")),
            "acao": _col(e, "codigo_acao"), "acao_nome": _col(e, "acao"),
            **_favorecido(_col(e, "codigo_favorecido"), _col(e, "favorecido"), _col(e, "observacao")),
        })
        # nos arquivos diarios a especie vem sempre 'Nao se aplica': o empenho
        # emitido no dia e o original. Itens de empenho que nao esta no arquivo
        # do dia sao inscricao/reinscricao automatica em restos a pagar (fora).
        esp = (especie or "").lower()
        if esp.startswith("original") or esp.startswith("n") or not esp:
            originais[e["codigo_empenho"]] = (data, e.get("codigo_unidade_gestora"))

    for it in bruto["item_empenho"]:
        emp = it["codigo_empenho"]
        if emp not in originais:
            continue
        nat8 = _natureza_por_partes(it, com_subelemento=True)
        if not pls_map.elemento_relevante(nat8[:6] if nat8 else None):
            continue
        data, ug = originais[emp]
        out.itens.append(_item(
            {**_tempo(data), "ug": ug}, emp, nat8, _col(it, "descricao"),
            sequencial=_col(it, "sequencial"), subelemento=_col(it, "subelemento_de_despesa"),
            quantidade=parse_valor(_col(it, "quantidade")), valor_unitario=parse_valor(_col(it, "valor_unitario")),
            valor=parse_valor(_col(it, "valor_atual", "valor_total")),
        ))

    for fase, arq, chave, col_valor in ((2, "liquidacao", "codigo_liquidacao", "valor_liquidado"), (3, "pagamento", "codigo_pagamento", "valor_pago")):
        docs = {d[chave]: d for d in bruto[arq]}
        for imp in bruto[f"{arq}_impactados"]:
            doc = docs.get(imp[chave])
            if doc is None:
                continue
            nat8 = _nat8_completa(_col(imp, "codigo_natureza_despesa_completa"), _col(imp, "subitem"))
            relevante = pls_map.elemento_relevante(nat8[:6] if nat8 else None)
            # acao acompanhada pelo PLS (ex.: 4572 capacitacao) entra com qualquer natureza
            if not relevante and (acoes or {}).get(imp.get("codigo_empenho")) not in pls_map.acoes():
                continue
            data = _data_iso(_col(doc, "data_emissao")) or dia.isoformat()
            valor = parse_valor(_col(imp, col_valor)) or 0.0
            out.fatos.append(_fato(
                {**_tempo(data), "ug": doc.get("codigo_unidade_gestora")}, fase, imp[chave],
                _col(doc, "tipo_documento"), imp.get("codigo_empenho"), _col(imp, "subitem"), nat8,
                liq=valor if fase == 2 else 0.0, pago=valor if fase == 3 else 0.0,
                rp_pago=parse_valor(_col(imp, "valor_restos_a_pagar_pagos")) or 0.0,
                rp_insc=parse_valor(_col(imp, "valor_restos_a_pagar_inscritos")),
                rp_canc=parse_valor(_col(imp, "valor_restos_a_pagar_cancelado")),
                fav=_favorecido(_col(doc, "codigo_favorecido"), _col(doc, "favorecido"), _col(doc, "observacao")),
            ))
    return out


# ---------------------------------------------------------------- fonte 2: API (dias sem arquivo)

def _nat6_api(doc: dict) -> str | None:
    return pls_map.natureza6(doc.get("categoria"), doc.get("grupo"), doc.get("modalidade"), doc.get("elemento"))


def _fav_api(doc: dict) -> dict:
    return _favorecido(doc.get("codigoFavorecido"), doc.get("nomeFavorecido") or doc.get("favorecido"), doc.get("observacao"))


def _dia_api(api: PortalApi, dia: date, nat6_por_empenho: dict[str, str]) -> Dia:
    out = Dia(fonte="api")
    for ug in config.UGS:
        for doc in api.documentos(ug, 1, dia):
            nat6 = _nat6_api(doc)
            data = _data_iso(doc.get("data")) or dia.isoformat()
            if nat6:
                nat6_por_empenho[doc["documento"]] = nat6
            out.empenhos.append({
                **_tempo(data), "ug": ug, "documento": doc.get("documento"), "especie": doc.get("especie"),
                "natureza6": nat6, "elemento": doc.get("elemento"), "valor": parse_valor(doc.get("valor")),
                **_fav_api(doc),
            })
            if (doc.get("especie") or "").lower().startswith("original") and pls_map.elemento_relevante(nat6):
                for it in api.itens_empenho(doc["documento"]):
                    nat8 = pls_map.natureza8(nat6, it.get("codigoSubelemento"))
                    out.itens.append(_item(
                        {**_tempo(data), "ug": ug}, doc["documento"], nat8, it.get("descricao"),
                        sequencial=it.get("sequencial"), subelemento=it.get("descricaoSubelemento"),
                        quantidade=None, valor_unitario=None, valor=parse_valor(it.get("valorAtual")),
                    ))
        for fase in FASES_FATO:
            for doc in api.documentos(ug, fase, dia):
                nat6_doc = _nat6_api(doc)
                if not pls_map.elemento_relevante(nat6_doc):
                    continue
                data = _data_iso(doc.get("data")) or dia.isoformat()
                for imp in api.empenhos_impactados(doc["documento"], fase):
                    # natureza da NE (uma OB pode pagar empenhos de elementos
                    # diferentes); senao a do proprio documento
                    nat6 = nat6_por_empenho.get(imp.get("empenho")) or nat6_doc
                    nat8 = pls_map.natureza8(nat6, imp.get("subitem")) or nat6
                    out.fatos.append(_fato(
                        {**_tempo(data), "ug": ug}, fase, doc["documento"], doc.get("especie"),
                        imp.get("empenho"), imp.get("subitem"), nat8,
                        liq=parse_valor(imp.get("valorLiquidado")) or 0.0,
                        pago=parse_valor(imp.get("valorPago")) or 0.0,
                        rp_pago=parse_valor(imp.get("valorRestoPago")) or 0.0,
                        rp_insc=parse_valor(imp.get("valorRestoInscrito")),
                        rp_canc=parse_valor(imp.get("valorRestoCancelado")),
                        fav=_fav_api(doc),
                    ))
    return out


# ---------------------------------------------------------------- extract + transform

def extract_transform(janela: Janela, bulk: PortalBulk, api: PortalApi | None) -> tuple[dict[str, pd.DataFrame], dict]:
    empenhos: list[dict] = []
    itens: list[dict] = []
    fatos: list[dict] = []
    nat6_por_empenho: dict[str, str] = {}
    fontes = {"arquivo": 0, "api": 0, "sem dados": 0}
    sem_dados: list[date] = []

    dias = janela.dias(ate=date.today())
    print(f"Despesas: {len(dias)} dias ({janela}), UGs {', '.join(config.UGS)}", flush=True)
    acoes = acoes_por_empenho()
    for n, dia in enumerate(dias, 1):
        bruto = bulk.dia(dia)
        if bruto is not None:
            d = _dia_bulk(bruto, dia, acoes)
        elif api is not None:
            d = _dia_api(api, dia, nat6_por_empenho)
        else:
            sem_dados.append(dia)
            fontes["sem dados"] += 1
            continue
        fontes[d.fonte] += 1
        empenhos += d.empenhos
        itens += d.itens
        fatos += d.fatos
        if n % 30 == 0:
            print(f"  ate {dia}: {fontes['arquivo']} dias por arquivo, {fontes['api']} pela API", flush=True)

    if sem_dados:
        print(f"  atencao: {len(sem_dados)} dias sem arquivo publicado e sem PORTAL_API_KEY para cobrir "
              f"({sem_dados[0]} .. {sem_dados[-1]}) -- ficam de fora ate o arquivo sair")

    fato = pd.DataFrame(fatos)
    if not fato.empty:
        # acao orcamentaria pelo empenho impactado; empenho anterior ao cache fica sem acao
        fato["acao"] = fato["empenho"].map(acoes)
    frames = {COL_FATO: fato, COL_EMPENHOS: pd.DataFrame(empenhos), COL_ITENS: pd.DataFrame(itens)}
    return frames, {"fontes": fontes, "sem_dados": sem_dados}


def acoes_por_empenho() -> dict[str, str]:
    """empenho -> codigo da acao orcamentaria, de TODOS os arquivos diarios em
    cache (nao so da janela): o pagamento de hoje pode ser de empenho de anos
    atras (restos a pagar), e so o arquivo do dia da emissao traz a acao."""
    out: dict[str, str] = {}
    for arq in sorted((config.RAW_DIR / "portal_bulk").glob("*/*.json")):
        for e in read_json(arq).get("dados", {}).get("empenho", []):
            acao = _col(e, "codigo_acao")
            if acao:
                out[e["codigo_empenho"]] = acao
    return out


# ---------------------------------------------------------------- load

def load(frames: dict[str, pd.DataFrame], *, dry_run: bool = False) -> None:
    for col, df in frames.items():
        if df.empty:
            print(f"'{col}': nada a gravar no periodo")
            continue
        if not dry_run:
            save_processed(df, col, replace_on="periodo")
        replace_by(col, df, "periodo", dry_run=dry_run)


def _relatorio(frames: dict[str, pd.DataFrame]) -> None:
    fato = frames[COL_FATO]
    if fato.empty:
        return
    liq = fato[fato["fase"] == "liquidacao"]
    pago = fato[fato["fase"] == "pagamento"]
    # restos a pagar liquidados vem com valor liquidado = 0 nos arquivos do
    # Portal; o valor so aparece no pagamento -- por isso "pago" e a medida
    # principal de consumo do painel
    report_counts("pago por tema, inclui restos a pagar (R$)", pago.groupby("tema_codigo")["valor"].sum().round(2).to_dict())
    report_counts("liquidado por tema, exercicio corrente (R$)", liq.groupby("tema_codigo")["valor"].sum().round(2).to_dict())
    curtas = liq["natureza"].fillna("").str.len() < 8
    if curtas.any():
        print(f"  atencao: {int(curtas.sum())} linhas sem subitem resolvido (natureza < 8 digitos)")
    _validar_tesouro(fato)
    nc = pago[pago["tema_codigo"] == pls_map.NAO_CLASSIFICADO]
    if not nc.empty:
        top = nc.groupby("natureza")["valor"].sum().sort_values(ascending=False).head(5)
        print("  naturezas relevantes sem tema (candidatas ao mapeamento):")
        for nat, v in top.items():
            print(f"    {nat}: R$ {v:,.2f}")


def _validar_tesouro(fato: pd.DataFrame) -> None:
    """Compara com a exportacao do Tesouro Gerencial (README, secao Validacao).

    Colunas: ano;natureza;liquidado;pago  (a antiga ano;natureza;valor vale
    como liquidado). A exportacao pode trazer todas as naturezas da UFPB --
    so as que estao no mapeamento PLS entram na comparacao.
    """
    if not VALIDACAO_TG.exists():
        print(f"  (sem {VALIDACAO_TG.name} para validacao cruzada -- ver README)")
        return
    cols = pd.read_csv(VALIDACAO_TG, sep=None, engine="python", nrows=0).columns.str.strip().str.lower()
    anos = {str(a) for a in fato["ano"].unique()}
    for metrica, fase in (("liquidado", "liquidacao"), ("pago", "pagamento")):
        coluna = metrica if metrica in cols else ("valor" if metrica == "liquidado" and "valor" in cols else None)
        if coluna is None:
            continue
        esperado = load_expected_csv(VALIDACAO_TG, ["ano", "natureza"], coluna, lower_cols=True)
        esperado = {
            k: v for k, v in esperado.items()
            if k.split("|")[0] in anos
            and pls_map.classificar_natureza(k.split("|")[1]).tema_codigo != pls_map.NAO_CLASSIFICADO
        }
        f = fato[fato["fase"] == fase]
        atual = f.assign(ano=f["ano"].astype(str)).groupby(["ano", "natureza"])["valor"].sum()
        report_counts(f"{metrica} x Tesouro Gerencial (ano|natureza)", {f"{a}|{n}": round(v, 2) for (a, n), v in atual.items()}, esperado)
    _validar_tesouro_mensal(fato)


def _validar_tesouro_mensal(fato: pd.DataFrame, *, tolerancia: float = 0.01, top: int = 8) -> None:
    """Mes a mes contra data/validacao/tesouro_gerencial_mensal.csv (gerado
    pelo conversor). Muitas linhas -- imprime so o resumo e as maiores
    divergencias em R$, para achar em que mes uma natureza descola."""
    arq = VALIDACAO_TG.with_name("tesouro_gerencial_mensal.csv")
    if not arq.exists():
        return
    ref = pd.read_csv(arq, sep=";", dtype=str)
    for c in ("liquidado", "pago"):
        ref[c] = ref[c].str.replace(",", ".").astype(float)
    ref = ref[ref["periodo"].isin(set(fato["periodo"]))]
    if ref.empty:
        return
    mapeada = ref["natureza"].map(lambda n: pls_map.classificar_natureza(n).tema_codigo != pls_map.NAO_CLASSIFICADO)
    ref = ref.loc[mapeada.astype(bool)]
    for metrica, fase in (("liquidado", "liquidacao"), ("pago", "pagamento")):
        # mesmo recorte dos dois lados: natureza sem tema entraria so pelo ETL, contra TG zerado
        # e so os meses que o TG cobre: mes fora dele contaria como divergencia contra zero
        f = fato[(fato["fase"] == fase) & (fato["tema_codigo"] != pls_map.NAO_CLASSIFICADO)
                 & fato["periodo"].isin(set(ref["periodo"]))]
        atual = f.groupby(["periodo", "natureza"])["valor"].sum().rename("etl")
        cmp = ref.set_index(["periodo", "natureza"])[metrica].rename("tg").to_frame().join(atual, how="outer").fillna(0.0)
        cmp = cmp[(cmp["tg"].abs() > 1) | (cmp["etl"].abs() > 1)]
        if cmp.empty:
            continue
        cmp["dif"] = cmp["etl"] - cmp["tg"]
        ok = (cmp["dif"].abs() <= tolerancia * cmp["tg"].abs().clip(lower=1)).sum()
        print(f"\n=== {metrica} x Tesouro Gerencial, mes a mes: {ok} de {len(cmp)} (periodo|natureza) dentro de {tolerancia:.0%} ===")
        piores = cmp.reindex(cmp["dif"].abs().sort_values(ascending=False).index).head(top)
        for (per, nat), r in piores.iterrows():
            if abs(r["dif"]) > tolerancia * max(abs(r["tg"]), 1):
                print(f"  {per} {nat}: ETL {r['etl']:,.2f} x TG {r['tg']:,.2f} (dif {r['dif']:+,.2f})")


def run(*, dry_run: bool = False, inicio: str | None = None, fim: str | None = None, offline: bool = False, **_: object) -> None:
    janela = Janela.de_args(inicio, fim)
    bulk = PortalBulk(offline=offline)
    api = PortalApi(offline=offline) if config.PORTAL_API_KEY else None
    frames, info = extract_transform(janela, bulk, api)

    print(f"\nArquivos diarios: {bulk.downloads} baixados, {bulk.cache_hits} do cache, {len(bulk.nao_publicados)} ainda nao publicados")
    if bulk.indisponiveis:
        print(f"  atencao: {len(bulk.indisponiveis)} dia(s) recusado(s) pelo Portal, sem dados: "
              f"{', '.join(str(d) for d in bulk.indisponiveis)}")
    if api is not None:
        print(f"API: {api.calls} chamadas, {api.cache_hits} respostas do cache")
    report_counts("dias por fonte", info["fontes"])
    report_counts("despesas (documentos)", {col: len(df) for col, df in frames.items()})
    _relatorio(frames)

    # mes com dia sem dado nenhum nao pode substituir o que ja estava gravado
    incompletos = sorted({d.strftime("%Y-%m") for d in info["sem_dados"]})
    if incompletos:
        print(f"  meses incompletos nao serao gravados: {', '.join(incompletos)}")
        frames = {c: df[~df["periodo"].isin(incompletos)] if not df.empty else df for c, df in frames.items()}
    load(frames, dry_run=dry_run)


if __name__ == "__main__":
    run()
