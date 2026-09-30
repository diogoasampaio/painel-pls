"""CLI do ETL do Painel de Sustentabilidade (PLS) da UFPB.

Uso:
    python run.py referencias [--dry-run]
    python run.py despesas   [--inicio AAAA-MM] [--fim AAAA-MM] [--dry-run] [--offline]
    python run.py viagens    [--inicio AAAA-MM] [--fim AAAA-MM] [--dry-run]
    python run.py compras    [--inicio AAAA-MM] [--refazer] [--offline]      # contratacoes no PNCP (editais e atas)
    python run.py avn        [--dry-run]                                    # pedidos do AVN (atestados nos processos de pagamento, SIPAC)
    python run.py quantidades [--dry-run]                                    # copos, papel A4 e toner: quantidade pelo preco da compra (PNCP)
    python run.py cnpj       [--refazer] [--offline]                           # porte/UF dos fornecedores (Receita, ~7 GB lidos em fluxo)
    python run.py evg        [--inicio AAAA-MM] [--fim AAAA-MM] [--offline]   # cursos da EVG/ENAP (UFPB declarada)
    python run.py acoes      [--dry-run]    # plano de acoes do PLS x acompanhamento dos responsaveis
    python run.py ipca       [--dry-run]
    python run.py faturas    [--inicio AAAA-MM] [--fim AAAA-MM] [--refazer]   # kWh/m3 das faturas no SIPAC (depois de despesas)
    python run.py inep       [--inicio AAAA-MM] [--fim AAAA-MM] [--dry-run]
    python run.py indicadores [--dry-run]
    python run.py metas      [--dry-run]    # catalogo do PLS x valores (automaticos + lancados)
    python run.py formularios [--dry-run]   # envios dos formularios do painel -> CSVs de acompanhamento/valores
    python run.py execucao   [--dry-run]    # indice sintetico de execucao do PLS e faixas dos indicadores
    python run.py diario     [--dry-run]    # formularios, metas e acoes (timer diario)
    python run.py saude      [--dry-run]    # confere o que ficou pendente e manda o alerta por e-mail
    python run.py mensal     [--dry-run]    # tudo, na ordem certa (usado pelo timer), e a saude no fim

Sem --inicio/--fim a janela e os dois ultimos meses fechados (o Portal
publica com atraso, entao o mes anterior e sempre reprocessado). Para a
carga historica, passe a janela explicita -- o cache em data/raw/ permite
interromper e retomar.

--so-arquivos: grava data/processed/*.parquet e nao toca no Mongo.
--offline (despesas): nao chama a API, so le o que ja esta em cache.
"""

import argparse
import sys
import traceback

from common import config
from acoes.load_acoes import run as run_acoes
from despesas.load_despesas import run as run_despesas
from evg.load_evg import run as run_evg
from cnpj.load_cnpj import run as run_cnpj
from compras.load_compras import run as run_compras
from compras.avn import run as run_avn
from compras.quantidades import run as run_quantidades
from execucao.build_execucao import run as run_execucao
from faturas.load_faturas import run as run_faturas
from fator_sin.load_fator_sin import run as run_fator_sin
from formularios.formularios import run as run_formularios
from indicadores.build_indicadores import run as run_indicadores
from inep.load_inep import run as run_inep
from ipca.load_ipca import run as run_ipca
from metas.load_metas import run as run_metas
from referencias.load_referencias import run as run_referencias
from saude.verificar import run as run_saude
from viagens.load_viagens import run as run_viagens

LOADERS = {
    "referencias": run_referencias,
    "despesas": run_despesas,
    "faturas": run_faturas,  # le o cache dos arquivos diarios de despesas
    "viagens": run_viagens,
    "compras": run_compras,  # contratacoes no PNCP: editais (N10), compras compartilhadas (N11)
    "avn": run_avn,  # pedidos do Almoxarifado Virtual Nacional atestados nos processos de pagamento (SIPAC)
    "quantidades": run_quantidades,  # copos, papel A4 e toner: valor empenhado / preco da compra no PNCP
    "cnpj": run_cnpj,  # porte e UF dos fornecedores (cadastro aberto de CNPJ da Receita)
    "evg": run_evg,  # cursos da Escola Virtual de Governo (ENAP), bimestral
    "ipca": run_ipca,
    "fator_sin": run_fator_sin,  # fator mensal de CO2 do SIN (MCTI), escopo 2 do N03
    "inep": run_inep,
    "indicadores": run_indicadores,  # le o que os modulos de fonte gravaram
    "formularios": run_formularios,  # envios do painel (Mongo) -> CSVs de acompanhamento e valores informados
    "metas": run_metas,  # le pls_indicadores
    "acoes": run_acoes,  # plano de acoes do PLS x acompanhamento semestral (usa pls_indicadores)
    "execucao": run_execucao,  # indice sintetico do PLS e faixas (depois de metas e acoes)
    "saude": run_saude,  # o que a carga deixou pendente -> pls_saude_carga + e-mail
}

# carga mensal automatica: INEP fica de fora (anual, rodar a mao quando o censo sair)
MENSAL = ["referencias", "ipca", "fator_sin", "despesas", "faturas", "viagens", "compras", "avn", "quantidades", "cnpj", "evg", "indicadores", "formularios", "metas", "acoes", "execucao"]
# diario: leva ao painel no dia seguinte o que os setores preencheram nos formularios
DIARIO = ["formularios", "metas", "acoes", "execucao"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("fonte", choices=[*LOADERS.keys(), "mensal", "diario"])
    parser.add_argument("--dry-run", action="store_true", help="processa e reporta totais sem gravar no Mongo nem em data/processed")
    parser.add_argument("--inicio", help="primeiro mes da janela (AAAA-MM)")
    parser.add_argument("--fim", help="ultimo mes da janela (AAAA-MM)")
    parser.add_argument("--offline", action="store_true", help="despesas: usa so o cache bruto, sem chamar a API")
    parser.add_argument("--refazer", action="store_true", help="faturas: consulta de novo os processos que nao tiveram fatura legivel")
    parser.add_argument("--so-arquivos", action="store_true", help="grava so data/processed (parquet), sem Mongo")
    args = parser.parse_args()
    if args.so_arquivos:
        config.SO_ARQUIVOS = True

    kw = dict(dry_run=args.dry_run, inicio=args.inicio, fim=args.fim, offline=args.offline, refazer=args.refazer)
    if args.fonte != "mensal":
        for fonte in DIARIO if args.fonte == "diario" else [args.fonte]:
            print(f"\n######## {fonte} ########", flush=True)
            LOADERS[fonte](**kw)
        return
    # carga mensal: modulo que falha nao derruba os seguintes (os derivados usam o
    # parquet anterior); a falha vai para a saude da carga e o processo sai com 1
    falhas: dict[str, str] = {}
    for fonte in MENSAL:
        print(f"\n######## {fonte} ########", flush=True)
        try:
            LOADERS[fonte](**kw)
        except Exception as e:
            traceback.print_exc()
            falhas[fonte] = f"{type(e).__name__}: {e}"
    print("\n######## saude ########", flush=True)
    run_saude(**kw, falhas=falhas)
    if falhas:
        sys.exit(1)


if __name__ == "__main__":
    main()
