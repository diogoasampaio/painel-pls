from fastapi import APIRouter

from app.execucao_routes import register_execucao_routes
from app.formularios_routes import register_formularios_routes
from app.metas_routes import register_metas_routes
from app.panel_routes import register_panel_routes
from app.panels import PLS_PANELS
from app.saude_routes import register_saude_routes

router = APIRouter(prefix="/pls", tags=["pls"])

# /metas, /saude, /execucao e /formularios antes de /{slug}: senao seriam lidos como slug de painel
register_metas_routes(router)
register_saude_routes(router)
register_execucao_routes(router)
register_formularios_routes(router)
register_panel_routes(router, panels=PLS_PANELS)
