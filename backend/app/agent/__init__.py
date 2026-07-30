"""Пакет агента-стилиста.

Публичный API слоя — интерфейс `Agent`, фабрика `build_agent` и доменные схемы.
Остальной код импортирует отсюда, не заглядывая в конкретные реализации.
"""

from app.agent.base import LLM, Agent, Catalog, Retriever, Vision
from app.agent.factory import build_agent
from app.agent.schemas import (
    Appearance,
    Constraints,
    Item,
    Look,
    StyleProfile,
    StylistAction,
    StylistRequest,
    StylistResult,
)

__all__ = [
    "Agent",
    "LLM",
    "Retriever",
    "Catalog",
    "Vision",
    "build_agent",
    "Appearance",
    "Constraints",
    "Item",
    "Look",
    "StyleProfile",
    "StylistAction",
    "StylistRequest",
    "StylistResult",
]
