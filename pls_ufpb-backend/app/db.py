from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.config import MONGO_DB, MONGO_URI


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Cria o client Motor preso ao event loop do processo do uvicorn.

    Um client global criado fora do lifespan pode ficar preso a um event
    loop que ja fechou (acontece com TestClient/pytest-asyncio, que abrem
    um loop por teste) -- daí RuntimeError: Event loop is closed nas
    chamadas seguintes. Guardar em app.state evita isso.
    """
    app.state.mongo_client = AsyncIOMotorClient(MONGO_URI)
    try:
        yield
    finally:
        app.state.mongo_client.close()


def get_database(request: Request) -> AsyncIOMotorDatabase:
    return request.app.state.mongo_client[MONGO_DB]
