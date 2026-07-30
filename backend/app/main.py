"""Точка входа FastAPI-приложения.

Здесь: инициализация БД, наполнение каталога, создание агента-синглтона,
CORS и подключение роутеров.
"""

from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.agent import build_agent
from app.api import public
from app.config import get_settings
from app.database import init_db
from app.seed import seed_catalog

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Старт: таблицы, каталог и один агент на всё приложение (он грузит базу знаний).
    settings = get_settings()
    logger.info("Application start: agent_type=%s", settings.agent_type)
    await init_db()
    await seed_catalog(settings.catalog_snapshot)
    app.state.agent = build_agent()
    logger.info("Agent initialized: %s", type(app.state.agent).__name__)
    yield
    # Здесь при необходимости — освобождение ресурсов.


app = FastAPI(title="Stylist Agent API", version="1.0.0", lifespan=lifespan)

# CORS: разрешаем фронтенду ходить в API. Для учебного проекта — максимально просто.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(public.router)


@app.get("/health", tags=["infra"])
async def health() -> dict[str, str]:
    return {"status": "ok"}
