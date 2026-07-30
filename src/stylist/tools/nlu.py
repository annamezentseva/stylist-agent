"""NLU запроса: интент + ограничения одним структурным LLM-вызовом.

Заменяет ключевую эвристику router'а: модель понимает «Что идёт цветотипу лето?»
как вопрос, а из «образ на свидание до 8000 без юбки» достаёт повод/бюджет/avoid.
Текст-вызов ~200 токенов gpt-4o-mini => ~$0.0001 за сообщение.

STUB-режим и любая ошибка LLM откатываются на keyword_intent (детерминизм
бенчмарка + живучесть при недоступности API).
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

from ..config import settings
from .llm import get_client


class RequestNLU(BaseModel):
    """Что пользователь хочет и какие ограничения назвал (null = не сказал)."""
    intent: Literal["new_look", "refine", "question"] = "new_look"
    occasion: Optional[str] = None
    budget_rub: Optional[int] = None
    season: Optional[str] = None
    avoid: list[str] = Field(default_factory=list)


_PROMPT = (
    "Ты маршрутизатор бота-стилиста. По сообщению пользователя определи:\n"
    "- intent: 'question' — вопрос или просьба совета по стилю/цветам/сочетаниям; "
    "'refine' — просьба доработать/заменить уже собранный образ; иначе 'new_look'.\n"
    "- occasion: повод, если назван (офис, свидание, прогулка, вечеринка, спорт...).\n"
    "- budget_rub: бюджет в рублях, если назван (только число).\n"
    "- season: сезон НОСКИ одежды, если назван (лето, зима, деми...); не путай с "
    "цветотипом внешности («цветотип лето» — это НЕ сезон).\n"
    "- avoid: чего избегать, если сказано («без юбки», «не люблю принты» -> [\"юбка\", \"принты\"]).\n"
    "Не выдумывай: чего в тексте нет — оставляй null/пустой список."
)


def keyword_intent(text: str, state: dict) -> str:
    """Эвристика по ключевым словам — STUB-режим и фолбэк при ошибке LLM."""
    t = (text or "").lower()
    if any(w in t for w in ("совет", "идёт ли", "подойдёт", "подойдет", "как носить")):
        return "question"
    if state.get("photos") and not state.get("appearance"):
        return "photo"
    return "new_look"


def understand_request(text: str) -> RequestNLU:
    """Реальный LLM-вызов со структурным выводом (зовущий сам решает про STUB/фолбэк)."""
    comp = get_client().chat.completions.parse(
        model=settings.llm_model,
        messages=[
            {"role": "system", "content": _PROMPT},
            {"role": "user", "content": text or ""},
        ],
        response_format=RequestNLU,
    )
    return comp.choices[0].message.parsed or RequestNLU()
