"""Слой промптов.

Промпты — это тоже код, но с особым жизненным циклом: их часто правят, тюнят и
версионируют отдельно от логики. Поэтому держим их в изолированном слое, а не
размазываем строками по агенту.
"""

from app.agent.prompts.stylist import (
    PROMPT_APPEARANCE,
    PROMPT_TASTE,
    SYSTEM_PROMPT_ADVICE,
    SYSTEM_PROMPT_NLU,
    build_context,
    build_user_prompt,
)

__all__ = [
    "SYSTEM_PROMPT_NLU",
    "SYSTEM_PROMPT_ADVICE",
    "PROMPT_APPEARANCE",
    "PROMPT_TASTE",
    "build_context",
    "build_user_prompt",
]
