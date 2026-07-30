"""LLM-судья образа: оценка гармонии/уместности со структурным выводом.

Ключевой методологический принцип — ПРЕЗУМПЦИЯ ОСОЗНАННОГО ПРИЁМА: нарушение
классического правила не считается ошибкой, если читается как именованный
трендовый приём (колор-блокинг, тотал-лук, оверсайз-баланс, тотал-деним, микс
фактур — см. рубрику «трендовые приёмы» в data/knowledge_base/styling_rules.json).
Судья штрафует случайность и разнобой, а не смелость. Критерий различения —
правило trend-echo: приём поддержан (эхо цвета, повтор пропорции, лаконичный фон).

В STUB-режиме возвращает максимум (детерминизм бенчмарка). При ошибке LLM —
тоже максимум, чтобы не блокировать выдачу из-за недоступности судьи.
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from ..config import settings
from ..models import Constraints, Look, StyleProfile
from .llm import get_client


class JudgeVerdict(BaseModel):
    score: float = Field(ge=0, le=5, description="итоговая оценка образа 0–5")
    rationale: str = Field(default="", description="краткое обоснование по-русски")
    techniques: list[str] = Field(default_factory=list,
                                  description="опознанные осознанные приёмы, если есть")


_JUDGE_PROMPT = """Ты — стилист-эксперт. Оцени образ по шкале 0–5 по трём критериям:
1) цветовая схема: опознаваема ли (монохром / аналоговая / комплементарная /
   нейтраль+акцент / колор-блок)? случайный разнобой цветов — штраф;
2) уместность поводу и сезону;
3) соответствие вкусу пользователя (его стили/палитра) и целостность стиля вещей.

ПРЕЗУМПЦИЯ ОСОЗНАННОГО ПРИЁМА: нарушение классического правила — НЕ ошибка, если
читается как намеренный приём: колор-блокинг чистыми цветами, тотал-лук в одном
ярком цвете, розовый+красный, оверсайз с открытыми «точками лёгкости», тотал-деним
в разных оттенках, видимая многослойность, контраст фактур, athleisure.
Штрафуй случайность, а не смелость. Различай по поддержке (правило «эха»): приём
обычно повторён (эхо цвета в детали, согласованные пропорции) или поддержан
лаконичностью остального. Если пользователь устойчиво выбирает «нарушение» — это
его стиль, оценивай внутри его логики, а не против неё.

Профиль вкуса: {profile}
Повод: {occasion}
Образ (вещи): {items}"""


def llm_judge(look: Look, profile: StyleProfile, c: Constraints) -> dict:
    """Оценка образа: {'score': 0-5, 'rationale': str, 'techniques': [...]}."""
    if settings.stub_llm:
        return {"score": 5.0, "rationale": "stub: детерминированная оценка", "techniques": []}
    try:
        items_desc = "; ".join(
            f"{i.category}: {i.title} ({i.color}, теги: {', '.join(i.style_tags)})"
            for i in look.items
        )
        comp = get_client().chat.completions.parse(
            model=settings.llm_model,
            messages=[{
                "role": "user",
                "content": _JUDGE_PROMPT.format(
                    profile=profile.model_dump(exclude_defaults=True),
                    occasion=c.occasion or "не указан",
                    items=items_desc,
                ),
            }],
            response_format=JudgeVerdict,
        )
        verdict = comp.choices[0].message.parsed
        return verdict.model_dump() if verdict else {"score": 5.0, "rationale": "", "techniques": []}
    except Exception:
        # Судья недоступен — не блокируем выдачу (программные проверки critic остаются).
        return {"score": 5.0, "rationale": "judge недоступен, пропущен", "techniques": []}
