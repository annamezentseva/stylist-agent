"""FastAPI-зависимости (Dependency Injection).

Собираем сервис из его частей: сессия БД (на запрос) + агент (синглтон, создан
при старте) + настройки. Роутеры получают готовый StylistService.
"""

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent import Agent
from app.config import get_settings
from app.database import get_session
from app.services.stylist import StylistService


def get_agent(request: Request) -> Agent:
    """Агент создаётся один раз при старте (lifespan) и живёт в app.state."""
    return request.app.state.agent


def get_stylist_service(
    session: AsyncSession = Depends(get_session),
    agent: Agent = Depends(get_agent),
) -> StylistService:
    return StylistService(session, agent, get_settings())
