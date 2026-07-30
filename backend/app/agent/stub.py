"""Заглушка агента-стилиста — стартовая точка (как StubAgent в Workshop 1).

Пока настоящий агент не собран, приложение всё равно поднимается и отвечает
осмысленно: сообщает, что подбор ещё не реализован. Так фронт, БД и API
работают end-to-end с первой минуты, а «мозг» подключается позже переключением
AGENT_TYPE на `simple`.
"""

from app.agent.base import Agent
from app.agent.schemas import StylistAction, StylistRequest, StylistResult


class StubStylistAgent(Agent):
    async def handle(self, request: StylistRequest) -> StylistResult:
        return StylistResult(
            action=StylistAction.NEED_INFO,
            rationale="Агент-стилист ещё не реализован — это заглушка.",
            missing=["включите AGENT_TYPE=simple"],
        )
