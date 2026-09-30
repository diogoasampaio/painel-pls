from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from app.config import APP_ENV, FRONTEND_ORIGIN
from app.db import lifespan
from app.routers import pls

_is_prod = APP_ENV == "production"

app = FastAPI(
    title="Painel PLS UFPB API",
    docs_url=None if _is_prod else "/docs",
    redoc_url=None if _is_prod else "/redoc",
    lifespan=lifespan,
)

# API roda so em 127.0.0.1 -- so o Next.js (BFF) acessa, via fetch
# server-side. E somente leitura, salvo os POST dos formularios (token do
# setor, insert-only no Mongo). CORS restrito a essa unica origem mesmo
# assim, como segunda camada.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.include_router(pls.router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
