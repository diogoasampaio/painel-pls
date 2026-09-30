import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ETL_ROOT = Path(__file__).resolve().parent.parent

# MONGO_URI so e exigido na hora de gravar (common/mongo.py) -- dry-run e
# testes rodam sem banco.
MONGO_URI = os.environ.get("MONGO_URI", "")
MONGO_DB = os.environ.get("MONGO_DB", "painel_pls")
# --so-arquivos (run.py): grava so data/processed/, sem Mongo -- maquina
# local sem banco ou consumo direto pelo Power BI.
SO_ARQUIVOS = os.environ.get("SO_ARQUIVOS", "") == "1"

DATA_DIR = Path(os.environ.get("DATA_DIR", ETL_ROOT / "data"))
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
REF_DIR = ETL_ROOT / "ref"

# ---------------------------------------------------------------- instituicao
CODIGO_ORGAO_SIAFI = os.environ.get("CODIGO_ORGAO_SIAFI", "26240")
# UGs executoras da UFPB (Orgao UGE 26240), conferidas no Tesouro Gerencial:
# 153065 UFPB, 153066 SOF/UFPB, 153073 CCA (Areia), 153074 CCHSA (Bananeiras)
UGS = [ug.strip() for ug in os.environ.get("UGS", "153065,153066,153073,153074").split(",") if ug.strip()]
CO_IES_INEP = os.environ.get("CO_IES_INEP", "579")

# ---------------------------------------------------------------- Portal da Transparencia
PORTAL_API_BASE = os.environ.get("PORTAL_API_BASE", "https://api.portaldatransparencia.gov.br/api-de-dados")
PORTAL_API_KEY = os.environ.get("PORTAL_API_KEY", "")
# Limite oficial fica em torno de 90 req/min de dia (mais alto de madrugada).
# 80 deixa folga; em carga historica noturna pode subir.
PORTAL_RPM = int(os.environ.get("PORTAL_RPM", "80"))
# Dias do cache bruto mais novos que isto sao rebaixados de novo (o Portal
# publica documentos com alguns dias de atraso). Dias mais antigos ficam
# imutaveis no cache.
PORTAL_CACHE_DIAS = int(os.environ.get("PORTAL_CACHE_DIAS", "45"))
# Downloads por minuto dos arquivos diarios (dados abertos). O servidor da
# CGU bloqueia o IP (HTTP 405) depois de muitos downloads seguidos.
PORTAL_BULK_RPM = int(os.environ.get("PORTAL_BULK_RPM", "4"))
PORTAL_BULK_PAUSA_S = int(os.environ.get("PORTAL_BULK_PAUSA_S", "900"))
PORTAL_BULK_TENTATIVAS = int(os.environ.get("PORTAL_BULK_TENTATIVAS", "2"))
PORTAL_DOWNLOAD_BASE = os.environ.get("PORTAL_DOWNLOAD_BASE", "https://portaldatransparencia.gov.br/download-de-dados")

# Consulta publica de processos do SIPAC (faturas de energia e agua em PDF).
# Servidor da propria universidade: uma requisicao a cada SIPAC_PAUSA_S.
SIPAC_BASE = os.environ.get("SIPAC_BASE", "https://sipac.ufpb.br")
SIPAC_PAUSA_S = float(os.environ.get("SIPAC_PAUSA_S", "2"))
SIPAC_GUARDAR_PDF = os.environ.get("SIPAC_GUARDAR_PDF", "") == "1"

# ---------------------------------------------------------------- outras fontes
BCB_SGS_IPCA_URL = os.environ.get(
    "BCB_SGS_IPCA_URL", "https://api.bcb.gov.br/dados/serie/bcdata.sgs.433/dados"
)
INEP_MICRODADOS_URL = os.environ.get(
    "INEP_MICRODADOS_URL",
    "https://download.inep.gov.br/microdados/microdados_censo_da_educacao_superior_{ano}.zip",
)
MUNICIPIOS_COORDS_URL = os.environ.get(
    "MUNICIPIOS_COORDS_URL",
    "https://raw.githubusercontent.com/kelvins/municipios-brasileiros/main/csv/municipios.csv",
)
ESTADOS_COORDS_URL = os.environ.get(
    "ESTADOS_COORDS_URL",
    "https://raw.githubusercontent.com/kelvins/municipios-brasileiros/main/csv/estados.csv",
)
