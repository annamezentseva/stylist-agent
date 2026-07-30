"""Общий OpenAI-клиент для vision- и NLU-вызовов.

Один клиент на процесс (lru_cache): переиспользуем connection pool между
всеми обращениями к модели вместо пересоздания на каждый вызов.
"""
from __future__ import annotations

import os
from functools import lru_cache

from ..config import settings


@lru_cache(maxsize=1)
def get_client():
    import openai

    key = (settings.llm_api_key or settings.vision_api_key
           or os.getenv("OPENAI_API_KEY", ""))
    return openai.OpenAI(api_key=key or None)  # None -> SDK сам возьмёт OPENAI_API_KEY
