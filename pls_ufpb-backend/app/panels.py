"""Definicao dos paineis do PLS.

Cada PanelDef vira uma rota `GET /pls/{slug}` (ver app/panel_routes.py).
Um painel e um recorte da colecao `pls_indicadores` (formato longo, um
documento por periodo x tema x subtema x metrica -- gerada pelo modulo
`indicadores` do ETL):

  temas     tema_codigo incluidos (vazio = todos, usado na visao geral)
  metricas  metrica -> rotulo; a ordem define a ordem dos graficos
  destaque  metrica dos cards de topo (ultimo ano x anterior)

Os rotulos dos temas vem da colecao `pls_temas` (ref/temas_pls.csv do
ETL), nao daqui -- mudar nome de tema nao exige deploy da API.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class PanelDef:
    slug: str
    label: str
    temas: list[str] = field(default_factory=list)
    metricas: dict[str, str] = field(default_factory=dict)
    destaque: str = "pago"


PLS_FILTERS = ["ano", "tema_codigo", "subtema"]

# campo de valor que o cliente pode pedir em ?valor=
VALOR_CAMPOS = {
    "nominal": "valor_nominal",
    "real": "valor_real",
    "per_capita": "valor_real_per_capita",
    "por_m2": "valor_por_m2",  # area construida do campus (consumo) ou da UFPB
}

PLS_PANELS: list[PanelDef] = [
    PanelDef(
        slug="visao-geral",
        label="Visão geral",
        metricas={"pago": "Pago, inclui restos a pagar (R$)", "liquidado": "Liquidado no exercício (R$)"},
    ),
    PanelDef(
        slug="energia",
        label="Energia elétrica",
        temas=["energia"],
        metricas={
            "pago": "Pago, inclui restos a pagar (R$)",
            "consumo_kwh": "Consumo medido por campus (kWh)",
            "empenhado_itens": "Itens LED e fotovoltaica empenhados (R$)",
        },
    ),
    PanelDef(
        slug="agua",
        label="Água e esgoto",
        temas=["agua_esgoto"],
        metricas={"pago": "Pago, inclui restos a pagar (R$)", "consumo_m3": "Consumo medido por campus (m³)"},
    ),
    PanelDef(
        slug="material-consumo",
        label="Material de consumo",
        temas=["material_consumo"],
        metricas={
            "pago": "Pago, inclui restos a pagar (R$)",
            "empenhado_itens": "Papel, copos e toner empenhados (R$)",
        },
    ),
    PanelDef(
        slug="contratacoes",
        label="Compras e contratações",
        temas=["contratacoes", "compras_sustentaveis", "manutencao_predial", "residuos", "capacitacao"],
        metricas={"pago": "Pago, inclui restos a pagar (R$)", "empenhado_itens": "Itens com atributo sustentável (R$)"},
    ),
    PanelDef(
        slug="deslocamento",
        label="Deslocamento de pessoal",
        temas=["deslocamento"],
        metricas={
            "pago": "Pago em diárias, passagens e frota (R$)",
            "consumo_litros": "Combustível abastecido pela frota (L)",
            "viagens": "Viagens realizadas",
            "trechos_aereos": "Trechos aéreos",
            "km_aereo": "Distância aérea (km)",
            "co2e_kg": "Emissões estimadas (kg CO2e)",
        },
    ),
]


def find_panel(slug: str) -> PanelDef | None:
    return next((p for p in PLS_PANELS if p.slug == slug), None)
