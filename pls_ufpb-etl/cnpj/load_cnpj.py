"""Porte e sede dos fornecedores da UFPB (cadastro aberto de CNPJ da Receita) -> N12.

Duas colecoes:

pls_pagamentos_pj  pagamentos (pago + RP pago) a pessoa juridica por mes, UG,
                   natureza e CNPJ, so nas naturezas de contratacao
                   (ELEMENTOS_CONTRATACAO, aplicacao direta 90). Vem de todo
                   o cache diario do Portal (data/raw/portal_bulk) -- inclusive
                   naturezas fora do PLS, que o modulo despesas descarta.
pls_fornecedores   1 doc por CNPJ pago: porte da empresa (ME/EPP), UF e
                   municipio do estabelecimento, natureza juridica, CNAE,
                   opcao pelo Simples/MEI com datas.

Fonte do cadastro: repositorio de dados abertos da Receita (Nextcloud do
SERPRO, compartilhamento publico `gn672Ad4CF8N6TK`, lido por WebDAV), pasta
Dados/Cadastros/CNPJ/AAAA-MM. Os arquivos somam ~7 GB (Empresas ~1,4 GB,
Estabelecimentos ~5,3 GB, Simples ~0,3 GB): cada zip e baixado, lido em
blocos, filtrado pelos ~2 mil CNPJ pagos pela UFPB e apagado. O resultado de
cada zip fica em data/raw/cnpj/<mes>/<arquivo>.json (carga interrompida
retoma do zip seguinte). Com fornecedor novo, relê a pasta mais recente no
maximo a cada RELEITURA_DIAS (90); --refazer força a releitura.

Limites (constam da ficha do indicador):
- porte e o do cadastro na data da extracao, nao o da data do pagamento
  (o Simples/MEI traz datas de opcao e exclusao, guardadas para conferencia);
- UF e a do estabelecimento que recebeu (CNPJ de 14 digitos), nao a da matriz;
- agricultura familiar: nao ha empenho com amparo da Lei 12.512/2011 (PAA)
  nem 11.947/2009 no cache; o criterio fica previsto em AMPAROS_AGRICULTURA.
"""

from __future__ import annotations

import glob
import io
import re
import zipfile
from collections import defaultdict
from datetime import date
from pathlib import Path

import pandas as pd
import requests

from common import config
from common.mongo import replace_by
from common.storage import raw_path, read_json, save_processed, write_json
from common.text import parse_valor
from common.validation import report_counts

COL_FORNECEDORES = "pls_fornecedores"
COL_PAGAMENTOS = "pls_pagamentos_pj"

WEBDAV = "https://arquivos.receitafederal.gov.br/public.php/webdav/Dados/Cadastros/CNPJ/"
COMPARTILHAMENTO = ("gn672Ad4CF8N6TK", "")

# elementos de despesa que sao contratacao de fornecedor (material, servico de
# terceiro PJ, locacao de mao de obra, TI, obras e equipamentos)
ELEMENTOS_CONTRATACAO = {"30", "32", "33", "35", "37", "39", "40", "51", "52"}
AMPAROS_AGRICULTURA = re.compile(r"12\.?512|11\.?947|14\.?628")
UF_LOCAL = "PB"
RELEITURA_DIAS = 90
FINANCEIRA = "Instituição financeira (conta vinculada, arrecadação)"

PORTE = {"00": "Não informado", "01": "Microempresa", "03": "Empresa de pequeno porte", "05": "Demais"}

# layouts sem cabecalho (metadados da Receita, cnpj-metadados.pdf)
LAYOUT = {
    "Empresas": (["cnpj_basico", "razao_social", "natureza_juridica", "qualificacao", "capital_social", "porte",
                  "ente_federativo"], ["cnpj_basico", "razao_social", "natureza_juridica", "porte"]),
    "Estabelecimentos": (["cnpj_basico", "cnpj_ordem", "cnpj_dv", "matriz_filial", "nome_fantasia", "situacao",
                          "data_situacao", "motivo_situacao", "cidade_exterior", "pais", "data_inicio",
                          "cnae_principal", "cnae_secundaria", "tipo_logradouro", "logradouro", "numero",
                          "complemento", "bairro", "cep", "uf", "municipio", "ddd1", "telefone1", "ddd2",
                          "telefone2", "ddd_fax", "fax", "email", "situacao_especial", "data_situacao_especial"],
                         ["cnpj_basico", "cnpj_ordem", "cnpj_dv", "situacao", "cnae_principal", "uf", "municipio"]),
    "Simples": (["cnpj_basico", "opcao_simples", "data_opcao_simples", "data_exclusao_simples", "opcao_mei",
                 "data_opcao_mei", "data_exclusao_mei"], None),
}


# ---------------------------------------------------------------- pagamentos

def _nat8(completa) -> str | None:
    d = re.sub(r"\D", "", str(completa or ""))
    return d[:8] if len(d) >= 8 else (d if len(d) == 6 else None)


def _data(valor: str | None) -> str | None:
    m = re.match(r"(\d{2})/(\d{2})/(\d{4})", valor or "")
    return f"{m[3]}-{m[2]}-{m[1]}" if m else None


def _pega(linha: dict, prefixo: str):
    return next((v for k, v in linha.items() if k.startswith(prefixo)), None)


def pagamentos_pj(anos: tuple[str, ...] = ("2023", "2024", "2025", "2026")) -> tuple[pd.DataFrame, set[str]]:
    """Pagamentos a PJ nas naturezas de contratacao, de todo o cache diario.
    Devolve tambem os empenhos com amparo de agricultura familiar."""
    soma: dict[tuple, float] = defaultdict(float)
    agricultura: set[str] = set()
    for arq in sorted(f for a in anos for f in glob.glob(str(config.RAW_DIR / "portal_bulk" / a / "*.json"))):
        dados = (read_json(Path(arq)) or {}).get("dados") or {}
        for e in dados.get("empenho", []):
            if AMPAROS_AGRICULTURA.search(str(e.get("amparo") or "")):
                agricultura.add(e["codigo_empenho"])
        docs = {d["codigo_pagamento"]: d for d in dados.get("pagamento", [])}
        for imp in dados.get("pagamento_impactados", []):
            doc = docs.get(imp.get("codigo_pagamento"))
            if doc is None:
                continue
            cnpj = re.sub(r"\D", "", str(doc.get("codigo_favorecido") or ""))
            nat = _nat8(imp.get("codigo_natureza_despesa_completa"))
            if len(cnpj) != 14 or not nat or nat[2:4] != "90" or nat[4:6] not in ELEMENTOS_CONTRATACAO:
                continue
            data = _data(doc.get("data_emissao"))
            if not data:
                continue
            valor = (parse_valor(_pega(imp, "valor_pago")) or 0.0) + (parse_valor(_pega(imp, "valor_restos_a_pagar_pagos")) or 0.0)
            chave = (data[:7], doc.get("codigo_unidade_gestora"), nat, cnpj, imp.get("codigo_empenho"))
            soma[chave] += valor
    df = pd.DataFrame([(*k, v) for k, v in soma.items()],
                      columns=["periodo", "ug", "natureza", "cnpj", "empenho", "valor"])
    if not df.empty:
        df["agricultura_familiar"] = df["empenho"].isin(agricultura)
        df = (df.groupby(["periodo", "ug", "natureza", "cnpj", "agricultura_familiar"], as_index=False)["valor"].sum())
        df["ano"] = df["periodo"].str[:4].astype(int)
    return df, agricultura


# ---------------------------------------------------------------- cadastro da Receita

def _listar(pasta: str = "") -> list[tuple[str, int]]:
    r = requests.request("PROPFIND", WEBDAV + pasta, auth=COMPARTILHAMENTO, headers={"Depth": "1"}, timeout=120)
    r.raise_for_status()
    itens = []
    for resp in re.findall(r"<d:response>(.*?)</d:response>", r.text, re.S):
        href = re.search(r"<d:href>([^<]+)</d:href>", resp)[1]
        tam = re.search(r"<d:getcontentlength>(\d+)", resp)
        itens.append((href.rstrip("/").rsplit("/", 1)[-1], int(tam[1]) if tam else 0))
    return itens[1:]  # o primeiro e a propria pasta


def mes_mais_recente() -> str:
    return max(n for n, _ in _listar() if re.fullmatch(r"\d{4}-\d{2}", n))


def _baixar(url: str, destino: Path, tamanho: int, tentativas: int = 5) -> None:
    """Download com retomada (Range): o servidor derruba conexoes longas."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    for _ in range(tentativas):
        feito = destino.stat().st_size if destino.exists() else 0
        if tamanho and feito >= tamanho:
            return
        try:
            with requests.get(url, auth=COMPARTILHAMENTO, stream=True, timeout=120,
                              headers={"Range": f"bytes={feito}-"} if feito else {}) as r:
                r.raise_for_status()
                modo = "ab" if feito and r.status_code == 206 else "wb"
                with open(destino, modo) as f:
                    for bloco in r.iter_content(1 << 20):
                        f.write(bloco)
        except requests.RequestException as e:
            print(f"  conexao caiu em {destino.name} ({e.__class__.__name__}); retomando")
    if tamanho and destino.stat().st_size < tamanho:
        raise RuntimeError(f"{destino.name}: download incompleto")


def _filtrar(zip_path: Path, tipo: str, basicos: set[str], cnpjs: set[str]) -> list[dict]:
    nomes, usar = LAYOUT[tipo]
    out = []
    with zipfile.ZipFile(zip_path) as z:
        for membro in z.namelist():
            with z.open(membro) as f:
                for bloco in pd.read_csv(io.TextIOWrapper(f, encoding="latin-1"), sep=";", header=None, names=nomes,
                                         usecols=usar, dtype=str, chunksize=500_000, quotechar='"'):
                    bloco = bloco[bloco["cnpj_basico"].isin(basicos)]
                    if tipo == "Estabelecimentos" and not bloco.empty:
                        bloco = bloco.assign(cnpj=bloco["cnpj_basico"] + bloco["cnpj_ordem"] + bloco["cnpj_dv"])
                        bloco = bloco[bloco["cnpj"].isin(cnpjs)]
                    out.extend(bloco.astype(object).where(bloco.notna(), None).to_dict(orient="records"))
    return out


def extract(cnpjs: set[str], *, refazer: bool = False, offline: bool = False) -> dict:
    """Cadastro dos CNPJ pedidos. Cache em data/raw/cnpj/cadastro.json."""
    cache_path = raw_path("cnpj", "cadastro.json")
    cache = read_json(cache_path) if cache_path.exists() else {}
    if offline or (cache and not refazer and cnpjs <= set(cache.get("procurados", []))):
        return cache
    # fornecedor novo aparece quase todo mes: so rele os ~7 GB a cada
    # RELEITURA_DIAS; ate la os novos ficam "Sem cadastro na Receita"
    baixado = cache.get("baixado_em")
    if cache and not refazer and baixado and (date.today() - date.fromisoformat(baixado)).days < RELEITURA_DIAS:
        novos = len(cnpjs - set(cache.get("procurados", [])))
        print(f"CNPJ: {novos} fornecedores novos ficam sem cadastro ate a releitura (cache de {baixado})")
        return cache
    mes = mes_mais_recente()
    basicos = {c[:8] for c in cnpjs}
    arquivos = [(n, t) for n, t in _listar(mes + "/") if re.match(r"(Empresas|Estabelecimentos)\d\.zip$|Simples\.zip$", n)]
    print(f"CNPJ: {len(cnpjs)} fornecedores, pasta {mes}, {len(arquivos)} arquivos "
          f"({sum(t for _, t in arquivos) / 1e9:.1f} GB)")
    partes: dict[str, list[dict]] = defaultdict(list)
    for nome, tam in arquivos:
        tipo = re.match(r"[A-Za-z]+", nome)[0]
        parcial = raw_path("cnpj", mes, nome.replace(".zip", ".json"))
        if parcial.exists() and not refazer and set(read_json(parcial)["procurados"]) >= cnpjs:
            partes[tipo].extend(read_json(parcial)["linhas"])
            continue
        zip_path = raw_path("cnpj", mes, "_zip", nome)
        print(f"  {nome} ({tam / 1e6:.0f} MB)")
        _baixar(WEBDAV + f"{mes}/{nome}", zip_path, tam)
        linhas = _filtrar(zip_path, tipo, basicos, cnpjs)
        write_json(parcial, {"procurados": sorted(cnpjs), "linhas": linhas})
        zip_path.unlink()
        partes[tipo].extend(linhas)
        print(f"    {len(linhas)} linhas dos fornecedores")
    cache = {"mes": mes, "baixado_em": date.today().isoformat(), "procurados": sorted(cnpjs), **partes}
    write_json(cache_path, cache)
    return cache


def transform(cache: dict, cnpjs: set[str]) -> pd.DataFrame:
    base = pd.DataFrame({"cnpj": sorted(cnpjs)})
    base["cnpj_basico"] = base["cnpj"].str[:8]
    emp = pd.DataFrame(cache.get("Empresas") or [], columns=LAYOUT["Empresas"][1]).drop_duplicates("cnpj_basico")
    est = pd.DataFrame(cache.get("Estabelecimentos") or [],
                       columns=[*LAYOUT["Estabelecimentos"][1], "cnpj"]).drop_duplicates("cnpj")
    sim = pd.DataFrame(cache.get("Simples") or [], columns=LAYOUT["Simples"][0]).drop_duplicates("cnpj_basico")
    df = (base.merge(emp, on="cnpj_basico", how="left")
              .merge(est[["cnpj", "situacao", "cnae_principal", "uf", "municipio"]], on="cnpj", how="left")
              .merge(sim, on="cnpj_basico", how="left"))
    df["porte_descricao"] = df["porte"].map(PORTE)
    df["me_epp"] = df["porte"].isin(["01", "03"])
    df["sede_local"] = df["uf"] == UF_LOCAL
    df["no_cadastro"] = df["porte"].notna()
    df["mes_cadastro"] = cache.get("mes")
    return df


def categoria(fornecedores: pd.DataFrame) -> pd.Series:
    """Subtema do pagamento (mutuamente exclusivos) por CNPJ."""
    f = fornecedores.set_index("cnpj")
    porte = f["me_epp"].map({True: "ME/EPP", False: "Demais portes"})
    local = f["sede_local"].map({True: "da Paraíba", False: "de outros estados"})
    cat = (porte + " " + local).where(f["no_cadastro"], "Sem cadastro na Receita")
    # banco como favorecido em natureza de contratacao: deposito em conta
    # vinculada de terceirizada ou arrecadacao de fatura -- beneficiario real
    # e outro, fica fora da razao
    return cat.mask(f["cnae_principal"].fillna("").str.startswith("64"), FINANCEIRA)


def run(*, dry_run: bool = False, offline: bool = False, refazer: bool = False, **_: object) -> None:
    pag, agric = pagamentos_pj()
    if pag.empty:
        print("CNPJ: nenhum pagamento a PJ no cache do Portal (rode despesas antes)")
        return
    cnpjs = set(pag["cnpj"])
    report_counts("Pagamentos a PJ em contratacoes por ano (R$)", pag.groupby("ano")["valor"].sum().round(2).to_dict())
    print(f"CNPJ: empenhos com amparo de agricultura familiar: {len(agric)}")
    forn = transform(extract(cnpjs, refazer=refazer, offline=offline), cnpjs)
    pag["subtema"] = pag["cnpj"].map(categoria(forn))
    pag.loc[pag["agricultura_familiar"], "subtema"] = "Agricultura familiar"
    report_counts("Fornecedores por porte", forn["porte_descricao"].fillna("sem cadastro").value_counts().to_dict())
    report_counts("Fornecedores com sede na PB", forn["sede_local"].value_counts().rename(str).to_dict())
    report_counts("Pago por categoria (R$)", pag.groupby("subtema")["valor"].sum().round(2).to_dict())
    if not dry_run:
        save_processed(forn, COL_FORNECEDORES)
        save_processed(pag, COL_PAGAMENTOS)
    replace_by(COL_FORNECEDORES, forn, "cnpj_basico", dry_run=dry_run)
    replace_by(COL_PAGAMENTOS, pag, "periodo", dry_run=dry_run)


if __name__ == "__main__":
    run()
