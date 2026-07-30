"""Промпты и структурные схемы для LLM-вызовов агента-стилиста.

Как и в Workshop 1, промпт — это отдельный слой, а не строка внутри агента.
Здесь же лежат маленькие pydantic-схемы для структурных вызовов (NLU-разбор
запроса) — они идут в `LLM.complete_structured` и валидируют ответ модели.
"""

from __future__ import annotations

import re
from typing import Literal, Optional

from pydantic import BaseModel, Field

from app.agent.schemas import RetrievedRule


# =========================================================================
#  1. Разбор запроса (NLU): интент + ограничения одним структурным вызовом
# =========================================================================


class RequestNLU(BaseModel):
    """Что пользователь хочет и какие ограничения назвал (null = не сказал)."""

    intent: Literal["new_look", "refine", "question"] = "new_look"
    occasion: Optional[str] = None
    budget_rub: Optional[int] = None
    season: Optional[str] = None
    avoid: list[str] = Field(default_factory=list)


SYSTEM_PROMPT_NLU = (
    "Ты — маршрутизатор бота-стилиста. По сообщению пользователя определи:\n"
    "- intent: 'question' — вопрос/просьба совета по стилю, цветам, сочетаниям; "
    "'refine' — просьба доработать уже собранный образ; иначе 'new_look'.\n"
    "- occasion: повод, если назван (офис, свидание, прогулка, вечеринка, спорт...).\n"
    "- budget_rub: бюджет в рублях, если назван (только число).\n"
    "- season: сезон НОСКИ одежды, если назван (лето, зима, деми...); не путай с "
    "цветотипом внешности («цветотип лето» — это НЕ сезон).\n"
    "- avoid: чего избегать («без юбки», «не люблю принты» -> [\"юбка\", \"принты\"]).\n"
    "Не выдумывай: чего в тексте нет — оставляй null или пустой список."
)


# Ключевые слова для эвристического разбора (STUB-режим и фолбэк при ошибке LLM).
_QUESTION_MARKERS = ("совет", "идёт ли", "идет ли", "подойд", "как носить", "?", "сочета")
_OCCASION_MARKERS = {
    "офис": "офис", "работ": "офис", "свидан": "свидание", "прогул": "прогулка",
    "вечерин": "вечеринка", "вечер": "вечеринка", "спорт": "спорт",
}


def heuristic_nlu(text: str) -> RequestNLU:
    """Разбор без LLM: ключевые слова + число бюджета регуляркой."""
    t = (text or "").lower()

    intent: Literal["new_look", "refine", "question"] = "new_look"
    if any(m in t for m in _QUESTION_MARKERS):
        intent = "question"
    elif any(w in t for w in ("замен", "доработ", "другой", "переделай")):
        intent = "refine"

    occasion = next((v for k, v in _OCCASION_MARKERS.items() if k in t), None)

    budget = None
    m = re.search(r"(\d[\d\s]{2,})\s*(?:руб|₽|р\b|тыс|k)?", t)
    if m:
        budget = int(m.group(1).replace(" ", ""))

    avoid = []
    for m in re.finditer(r"без\s+([а-яё]+)", t):
        avoid.append(m.group(1))

    return RequestNLU(intent=intent, occasion=occasion, budget_rub=budget, avoid=avoid)


# =========================================================================
#  2. Совет по стилю (advice): ответ на вопрос по найденным правилам (RAG)
# =========================================================================


SYSTEM_PROMPT_ADVICE = """\
Ты — доброжелательный ИИ-стилист. Ответь на вопрос пользователя, опираясь ТОЛЬКО
на предоставленный КОНТЕКСТ из базы знаний по стилю (колористика, фигуры,
дресс-код, приёмы). Если в контексте нет нужного — честно скажи, что не уверен,
и не выдумывай. Отвечай кратко, по делу и на языке пользователя.
"""


def build_context(rules: list[RetrievedRule]) -> str:
    """Собираем найденные правила в единый блок КОНТЕКСТА для LLM."""
    if not rules:
        return "(база знаний ничего не вернула по этому запросу)"
    return "\n\n".join(f"[источник: {r.source}]\n{r.text}" for r in rules)


def build_user_prompt(question: str, context: str) -> str:
    """Пользовательское сообщение = вопрос + найденный контекст."""
    return f"КОНТЕКСТ:\n{context}\n\nВОПРОС ПОЛЬЗОВАТЕЛЯ:\n{question}"
