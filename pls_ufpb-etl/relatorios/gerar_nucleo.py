"""Pagina do nucleo do PLS (15 indicadores de ref/nucleo_pls.csv) para validacao
pela Comissao: aba de apresentacao (criterios e automacao) e aba do painel.

Valores: do indicador do catalogo (pls_metas) quando o nucleo aponta um; senao,
calculados aqui pela mesma regra do ETL (metas.load_metas._automatico)."""

import html
import math
import sys
from datetime import date
from pathlib import Path

import pandas as pd

ETL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ETL))
from metas import catalogo  # noqa: E402
from metas.load_metas import _automatico  # noqa: E402

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).with_name("nucleo_pls_ufpb.html")
FICHAS = "https://claude.ai/artifact/WzARzGDgoTKjA8GNNhCbu7"
e = html.escape
ANOS = [2023, 2024, 2025, 2026]

nucleo = pd.read_csv(ETL / "ref" / "nucleo_pls.csv", sep=";", dtype=str, keep_default_na=False)
eixos = pd.read_csv(ETL / "ref" / "eixos_pls.csv", sep=";", dtype=str).set_index("eixo_pls")["eixo"]
cat = pd.read_csv(ETL / "ref" / "indicadores_pls.csv", sep=";", dtype=str, keep_default_na=False).set_index("id")
metas = pd.read_parquet(ETL / "data" / "processed" / "pls_metas.parquet")
ind = pd.read_parquet(ETL / "data" / "processed" / "pls_indicadores.parquet")
_arq_acoes = ETL / "data" / "processed" / "pls_acoes.parquet"
acoes = pd.read_parquet(_arq_acoes) if _arq_acoes.exists() else pd.DataFrame()
_arq_exec = ETL / "data" / "processed" / "pls_execucao.parquet"
execucao = pd.read_parquet(_arq_exec) if _arq_exec.exists() else pd.DataFrame()
execucao = execucao[execucao["conjunto"] == "nucleo"] if not execucao.empty else execucao
parametros = pd.read_csv(ETL / "ref" / "indice_execucao.csv", sep=";", dtype=str).set_index("parametro")["valor"]

SITUACAO = {
    "automatizado": ("auto", "Automatizado"),
    "calcular": ("calc", "Dado já coletado, falta calcular"),
    "fonte_nova": ("nova", "Fonte pública nova"),
    "informado": ("inf", "Informado pela Comissão"),
}
FASE = {"0": "Pronto", "1": "Fase 1", "2": "Fase 2", "3": "Fase 3"}
META_SIT = {"atingida": ("ok", "Meta atingida"), "nao_atingida": ("ruim", "Meta não atingida"),
            "em_andamento": ("neutro", "Em andamento"), "linha_de_base": ("neutro", "Linha de base"),
            "historico": ("neutro", "Histórico"), "acompanhamento": ("neutro", "")}


def num(v, unidade=""):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "—"
    casas = 0 if abs(v) >= 100 or v == 0 else (1 if abs(v) >= 10 else 2)
    s = f"{v:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {s}" if unidade == "R$" else s


def valores(r) -> dict[int, dict]:
    """ano -> {valor, completo, situacao}"""
    out = {}
    if r.indicador_catalogo:
        m = metas[metas["indicador_id"] == r.indicador_catalogo]
        for x in m.itertuples():
            out[int(x.ano)] = {"valor": x.valor, "completo": bool(x.ano_completo), "situacao": x.situacao,
                               "alcance": getattr(x, "alcance_pct", None)}
    elif r.calculo:
        serie = _automatico(catalogo.parse_calculo(r.calculo), ind)
        meses = serie.attrs.get("meses", {})
        for a, v in serie.items():
            out[int(a)] = {"valor": float(v), "completo": meses.get(a, 0) == 12, "situacao": "acompanhamento"}
    if r.codigo == "N15" and not acoes.empty:  # cumprimento do plano de acoes (modulo acoes)
        ano = int(str(acoes["data_referencia"].iloc[0])[:4])
        out = {ano: {"valor": float(acoes["indice_cumprimento"].iloc[0]), "completo": False, "situacao": "acompanhamento"}}
    if r.codigo == "N03":  # hoje so viagens aereas, em kg: mostra em t
        out = {a: {**d, "valor": d["valor"] / 1000} for a, d in out.items()}
    return out


def cartao(r) -> str:
    cls, rot = SITUACAO[r.situacao]
    vals = valores(r)
    parcial_ind = r.situacao != "automatizado" and bool(vals)
    # valor provisorio fica na unidade do dado de hoje, nao na do indicador final
    unidade = r.unidade
    if parcial_ind:
        unidade = "tCO₂e" if r.codigo == "N03" else cat.loc[r.indicador_catalogo, "unidade"] if r.indicador_catalogo else r.unidade
    if vals:
        cels = []
        for a in ANOS:
            d = vals.get(a)
            if not d:
                cels.append(f'<div class="ano"><span class="a">{a}</span><b>—</b></div>')
                continue
            sit_cls, sit_rot = META_SIT.get(d["situacao"], ("neutro", ""))
            alc = d.get("alcance")
            if d["situacao"] == "nao_atingida" and alc is not None and alc == alc:
                sit_rot = f"{sit_rot} · alcance {alc:.0f}%"
            sit = f'<span class="sit {sit_cls}">{sit_rot}</span>' if sit_rot else ""
            parc = "" if d["completo"] else '<i>parcial</i>'
            cels.append(f'<div class="ano"><span class="a">{a} {parc}</span><b class="num">{e(num(d["valor"], unidade))}</b>{sit}</div>')
        corpo = f'<div class="anos">{"".join(cels)}</div>'
        if parcial_ind and r.hoje:
            corpo = f'<p class="hoje"><b>Valor provisório ({e(unidade)}):</b> {e(r.hoje)}</p>' + corpo
    else:
        corpo = (f'<div class="vazio-ind"><b>{FASE[r.fase]}</b> — {e(r.hoje or "Ainda sem valor")}. '
                 f'{e(r.observacao)}</div>')
    ficha = (f'<a class="ficha" href="{FICHAS}#{e(r.indicador_catalogo)}" target="_blank" rel="noopener">Como é construído →</a>'
             if r.indicador_catalogo else "")
    nota = f'<p class="obs">{e(r.observacao)}</p>' if vals and r.observacao else ""
    if r.codigo == "N15" and not acoes.empty:
        cont = acoes["situacao"].value_counts()
        partes_n15 = [f"{int(cont.get(k, 0))} {rot_}" for k, rot_ in (("concluida", "concluídas"), ("em_dia", "em dia"),
                      ("em_andamento", "em andamento"), ("atrasada", "atrasadas"),
                      ("vencida_sem_informacao", "com prazo vencido sem informação"), ("sem_informacao", "sem informação"))
                      if cont.get(k, 0)]
        nota = (f'<p class="hoje">{len(acoes)} ações: {", ".join(partes_n15)}. '
                f'<a href="#acoes" data-aba="tab-acoes">Ver o plano de ações →</a></p>') + nota
    return (
        f'<article class="ind {cls}" id="{e(r.codigo)}"><header><span class="cod">{e(r.codigo)}</span>'
        f'<span class="chip {cls}">{rot}</span>{"" if r.fase == "0" else f"<span class=fase>{FASE[r.fase]}</span>"}</header>'
        f'<h3>{e(r.indicador)}</h3>'
        f'<div class="formula"><code>{e(r.formula)}</code><em>{e(r.unidade)}</em></div>'
        f'{corpo}{nota}<p class="fonte"><b>Fonte:</b> {e(r.fonte)}</p>{ficha}</article>'
    )


def painel() -> str:
    partes = []
    ordem = [x for x in ["1", "2", "3", "4", "5", "6", "transversal"] if x in set(nucleo["eixo_pls"])]
    for eixo in ordem:
        sub = nucleo[nucleo["eixo_pls"] == eixo]
        nome = eixos.get(eixo, "Transversal: gestão do PLS")
        titulo = f"Eixo {eixo}" if eixo != "transversal" else "Transversal"
        partes.append(f'<section class="eixo"><h2><span>{titulo}</span> {e(nome)}</h2><div class="grade">'
                      + "".join(cartao(r) for r in sub.itertuples()) + "</div></section>")
    return "".join(partes)


def pct(v) -> str:
    return "—" if v is None or (isinstance(v, float) and math.isnan(v)) else f"{v:.1f}%".replace(".", ",")


def barra_faixas(linha, fx) -> str:
    segs = "".join(f'<span class="seg fx-{r.codigo}" style="flex:{int(linha.get(f"faixa_{r.codigo}", 0) or 0)}" '
                   f'title="{e(r.faixa)}">{int(linha.get(f"faixa_{r.codigo}", 0) or 0)}</span>'
                   for r in fx.itertuples() if int(linha.get(f"faixa_{r.codigo}", 0) or 0))
    return f'<div class="barra fx" role="img" aria-label="Indicadores por faixa de execução">{segs}</div>'


def bloco_execucao() -> str:
    """Indice sintetico, componentes, cobertura e faixas (modulo execucao do ETL)."""
    if execucao.empty:
        return ""
    fx = execucao[execucao["nivel"] == "faixa"].sort_values("ordem")
    geral = execucao[execucao["nivel"] == "geral"].sort_values("ano")
    atual = geral.iloc[-1]
    ano_m = int(atual["ano_metas"]) if atual["ano_metas"] == atual["ano_metas"] and atual["ano_metas"] is not None else int(atual["ano"])
    ref = geral[geral["ano"] == ano_m].iloc[0]
    legenda_fx = "".join(f'<li><span class="sw fx-{r.codigo}"></span>{e(r.faixa)}</li>' for r in fx.itertuples())
    eixos_ano = execucao[(execucao["nivel"] == "eixo") & (execucao["ano"] == ano_m)].sort_values("eixo_pls")
    linhas = "".join(
        f'<tr><th scope="row"><span>Eixo {e(str(r.eixo_pls))}</span>{e(eixos.get(str(r.eixo_pls), ""))}</th>'
        f'<td class="n">{pct(r.indice_metas)}</td><td class="n">{int(r.n_avaliados)} de {int(r.n_com_meta)}</td>'
        f'<td class="fxcel">{barra_faixas(r._asdict(), fx)}</td></tr>' for r in eixos_ano.itertuples())
    pm, pa = float(parametros["peso_metas"]) * 100, float(parametros["peso_acoes"]) * 100
    return f"""
    <section class="exec">
      <h2>Execução do plano · {int(atual["ano"])}</h2>
      <div class="kpis">
        <div class="kpi destaque"><b>{pct(atual["indice_sintetico"])}</b><span>índice sintético de execução ({pm:.0f}% metas + {pa:.0f}% ações)</span></div>
        <div class="kpi"><b>{pct(atual["indice_metas_usado"])}</b><span>alcance das metas ({ano_m}), média por eixo</span></div>
        <div class="kpi"><b>{pct(atual["indice_acoes"])}</b><span>cumprimento do plano de ações (N15)</span></div>
        <div class="kpi"><b>{int(ref["n_avaliados"])} de {int(ref["n_indicadores"])}</b><span>indicadores com meta avaliada em {ano_m}</span></div>
      </div>
      <p class="mini">Indicadores do núcleo por faixa de execução em {ano_m}:</p>
      {barra_faixas(ref.to_dict(), fx)}
      <ul class="legenda">{legenda_fx}</ul>
      <div class="tab exec-eixos"><table>
        <thead><tr><th>Eixo</th><th>Alcance das metas</th><th>Avaliados</th><th>Faixas</th></tr></thead>
        <tbody>{linhas}</tbody></table></div>
      <p class="obs" style="margin-top:.6rem">Com só {int(ref["n_com_meta"])} indicadores do núcleo com meta hoje, o índice ainda diz pouco sobre o plano: ele ganha sentido à medida que a Comissão fixar as metas (ver a Apresentação).</p>
    </section>"""


def tabela_metas() -> str:
    linhas = []
    for r in nucleo.itertuples():
        atual = "—"
        if r.indicador_catalogo and r.indicador_catalogo in cat.index:
            c = cat.loc[r.indicador_catalogo]
            atual = c["meta"] if c["tipo_meta"] != "acompanhamento" else "Sem meta (acompanhamento)"
        elif r.codigo == "N15":
            atual = "Sem meta (componente do índice)"
        else:
            atual = "Sem meta"
        cls = "ok" if atual not in ("—", "Sem meta") and not atual.startswith("Sem meta") else "falta"
        linhas.append(f'<tr><th scope="row"><span>{e(r.codigo)}</span>{e(r.indicador)}</th>'
                      f'<td class="{cls}">{e(atual)}</td><td>{e(r.meta_sugerida)}</td></tr>')
    return "".join(linhas)


SIT_ACAO = {
    "concluida": ("auto", "Concluída"), "em_dia": ("auto", "Em dia"), "em_andamento": ("nova", "Em andamento"),
    "nao_iniciada": ("calc", "Não iniciada"), "a_iniciar": ("inf", "A iniciar"), "pendente": ("calc", "Pendente no ciclo"),
    "atrasada": ("ruim", "Atrasada"), "vencida_sem_informacao": ("calc", "Prazo vencido, sem informação"),
    "sem_informacao": ("inf", "Sem informação"), "suspensa": ("inf", "Suspensa"), "cancelada": ("inf", "Cancelada"),
}
VERIF = {"painel": "Verificada pelo painel", "indicio": "Indício no painel", "informada": "Informada pelo responsável"}


def _mes(aaaamm: str) -> str:
    return f"{aaaamm[5:]}/{aaaamm[:4]}" if aaaamm else "—"


def aba_acoes() -> str:
    if acoes.empty:
        return '<p class="vazio-ind">Rode <code>python run.py acoes</code> para carregar o plano de ações.</p>'
    cont = acoes["situacao"].value_counts()
    resumo = "".join(f'<li><span class="chip {SIT_ACAO[k][0]}">{SIT_ACAO[k][1]}</span> <b>{int(v)}</b></li>'
                     for k, v in cont.items())
    partes = [f'<ul class="resumo-acoes">{resumo}</ul>']
    for eixo in ["1", "2", "3", "4", "5", "6", "transversal"]:
        sub = acoes[acoes["eixo_pls"] == eixo]
        if sub.empty:
            continue
        nome = eixos.get(eixo, "Governança do PLS (seção 7 e portarias)")
        titulo = f"Eixo {eixo}" if eixo != "transversal" else "Governança"
        linhas = []
        for a in sub.itertuples():
            cls, rot = SIT_ACAO.get(a.situacao, ("inf", a.situacao))
            ver = VERIF[a.verificacao] + (f"<small>{e(a.evidencia_painel)}</small>" if a.evidencia_painel else "")
            linhas.append(
                f'<tr><th scope="row"><span class="cod">{e(a.id)}</span>{e(a.acao)}<small>Meta: {e(a.meta)}</small></th>'
                f'<td>{e(a.responsavel)}</td><td class="num">{_mes(a.inicio)} a {_mes(a.fim)}</td>'
                f'<td>{"Entrega" if a.tipo == "entrega" else "Contínua"}</td><td>{ver}</td>'
                f'<td><span class="chip {cls}">{rot}</span></td></tr>')
        partes.append(f'<section class="eixo"><h2><span>{titulo}</span> {e(nome)}</h2><div class="tab acoes"><table>'
                      f'<thead><tr><th>Ação</th><th>Responsável</th><th>Prazo</th><th>Tipo</th><th>Verificação</th><th>Situação</th></tr></thead>'
                      f'<tbody>{"".join(linhas)}</tbody></table></div></section>')
    return "".join(partes)


def cobertura() -> str:
    linhas = []
    for eixo in ["1", "2", "3", "4", "5", "6"]:
        sub = nucleo[nucleo["eixo_pls"] == eixo]
        chips = "".join(f'<a class="chip {SITUACAO[r.situacao][0]}" href="#{e(r.codigo)}" data-ir="painel">{e(r.codigo)} {e(r.indicador)}</a>'
                        for r in sub.itertuples())
        linhas.append(f'<tr><th scope="row"><span>Eixo {eixo}</span>{e(eixos[eixo])}</th><td>{chips}</td></tr>')
    return "".join(linhas)


cont = nucleo["situacao"].value_counts()
auto = int(cont.get("automatizado", 0))
automatizaveis = int(len(nucleo) - cont.get("informado", 0))
barra = "".join(f'<span class="seg {SITUACAO[s][0]}" style="flex:{int(cont.get(s, 0))}">{int(cont.get(s, 0))}</span>'
                for s in SITUACAO if cont.get(s, 0))
legenda = "".join(f'<li><span class="sw {SITUACAO[s][0]}"></span>{SITUACAO[s][1]} <b>{int(cont.get(s, 0))}</b></li>' for s in SITUACAO)

TEMPLATE = Path(__file__).with_name("nucleo_template.html").read_text(encoding="utf-8")
pagina = (TEMPLATE.replace("{{N}}", str(len(nucleo))).replace("{{AUTO}}", str(auto))
          .replace("{{AUTOMATIZAVEIS}}", str(automatizaveis))
          .replace("{{PCT}}", str(round(100 * automatizaveis / len(nucleo))))
          .replace("{{BARRA}}", barra).replace("{{LEGENDA}}", legenda)
          .replace("{{COBERTURA}}", cobertura()).replace("{{PAINEL}}", painel())
          .replace("{{EXECUCAO}}", bloco_execucao()).replace("{{METAS}}", tabela_metas())
          .replace("{{PESO_METAS}}", f'{float(parametros["peso_metas"]) * 100:.0f}')
          .replace("{{PESO_ACOES}}", f'{float(parametros["peso_acoes"]) * 100:.0f}')
          .replace("{{N_COM_META}}", str(sum(1 for r in nucleo.itertuples() if r.indicador_catalogo in cat.index
                                             and cat.loc[r.indicador_catalogo, "tipo_meta"] != "acompanhamento")))
          .replace("{{ACOES}}", aba_acoes()).replace("{{N_ACOES}}", str(len(acoes)))
          .replace("{{FICHAS}}", FICHAS).replace("{{DATA}}", date.today().strftime("%d/%m/%Y")))
assert "{{" not in pagina
OUT.write_text(pagina, encoding="utf-8")
print(OUT, len(nucleo), auto, automatizaveis)
