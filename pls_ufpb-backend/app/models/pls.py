"""Modelos de resposta explicitos: so sai da API o que esta declarado aqui."""

from pydantic import BaseModel


class PainelResumo(BaseModel):
    slug: str
    label: str


class TemaOut(BaseModel):
    codigo: str
    label: str
    eixo: str | None = None


class FiltrosOut(BaseModel):
    anos: list[int]
    temas: list[TemaOut]
    metricas: list[str]


class MetricaOut(BaseModel):
    codigo: str
    label: str


class PontoSerie(BaseModel):
    periodo: str  # "2025" (granularidade ano) ou "2025-03" (mes)
    metrica: str
    grupo: str | None
    valor: float | None
    unidade: str | None


class Destaque(BaseModel):
    grupo: str | None
    ano: int
    valor: float
    ano_anterior: int | None
    valor_anterior: float | None
    variacao_pct: float | None


class PainelOut(BaseModel):
    slug: str
    label: str
    metricas: list[MetricaOut]
    valor: str
    granularidade: str
    por: str
    series: list[PontoSerie]
    destaques: list[Destaque]


class EixoOut(BaseModel):
    eixo_pls: str
    eixo: str
    descricao: str


class ValorMetaOut(BaseModel):
    ano: int
    valor: float | None
    # R$ corrigido pelo IPCA: valor = R$ de ref_ipca; valor_nominal = como foi pago (conferencia)
    valor_nominal: float | None = None
    ref_ipca: str | None = None
    origem: str
    fonte: str | None = None
    ano_completo: bool
    ano_referencia: int | None = None
    variacao_pct: float | None = None
    situacao: str
    # grau de alcance da meta no ano (0-100) e faixa (ref/faixas_execucao.csv)
    alcance_pct: float | None = None
    faixa: str | None = None


class IndicadorMetaOut(BaseModel):
    id: str
    eixo_pls: str
    tabela_pls: str | None = None
    objetivo: str
    indicador: str
    formula: str
    unidade: str
    meta: str
    tipo_meta: str
    meta_valor: float | None = None
    ano_base: int | None = None
    responsavel: str
    automacao: str
    tipo_fonte: str
    rota_automacao: str
    valores: list[ValorMetaOut]
    decisoes: list["DecisaoOut"] = []


class DecisaoOut(BaseModel):
    """Questao em aberto para a Comissao do PLS (ref/decisoes_comissao.csv)."""

    id: str
    questao: str
    contexto: str | None = None
    opcoes: str | None = None
    efeito: str | None = None
    situacao: str
    decisao: str | None = None


IndicadorMetaOut.model_rebuild()  # resolve a referencia adiantada a DecisaoOut


class MetasOut(BaseModel):
    eixos: list[EixoOut]
    indicadores: list[IndicadorMetaOut]
