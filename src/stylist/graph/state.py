"""Состояние графа LangGraph.

Единый объект, который течёт по узлам. Держим и «сырые» словари (для простоты
сериализации в трейсы/бенчмарк), и валидируем через Pydantic-модели внутри узлов.
"""
from __future__ import annotations

from typing import Annotated, Any, TypedDict

try:
    from langgraph.graph.message import add_messages
except Exception:  # pragma: no cover - позволяет импортировать без langgraph
    def add_messages(left: list, right: list) -> list:  # type: ignore
        return (left or []) + (right or [])


class StylistState(TypedDict, total=False):
    messages: Annotated[list, add_messages]

    user_id: str                 # id пользователя Telegram (для персонализации)
    request: str                 # текст пользователя
    intent: str                  # new_look | refine | question | photo

    photos: dict[str, list[str]]  # {"body": [...], "face": [...], "refs": [...]}
    appearance: dict[str, Any]    # Appearance.model_dump()
    style_profile: dict[str, Any]  # StyleProfile.model_dump()
    constraints: dict[str, Any]    # Constraints.model_dump()
    gate_tries: dict[str, int]     # сколько раз gate дёргал каждый сборщик профиля

    retrieved_items: list[dict]    # источник истины для composer
    candidate_looks: list[dict]    # Look.model_dump()
    critique: dict[str, Any]       # Critique.model_dump()
    iteration: int                 # счётчик петли самокоррекции
    final_looks: list[dict]

    answer: str                    # ответ advisor_qa
    tool_calls: list[dict]         # журнал вызовов инструментов (для eval)
