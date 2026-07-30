"""Конфигурация приложения.

Все настройки читаются из переменных окружения (.env). Один источник правды,
типизированный и провалидированный через pydantic-settings. Никаких «магических»
строк по коду — только `get_settings()`.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- База данных ---
    # По умолчанию SQLite-файл рядом с проектом: ничего поднимать не нужно.
    database_url: str = "sqlite+aiosqlite:///./stylist.db"

    # --- Выбор реализации агента ---
    # "simple" — RAG + каталог + композиция образа (рабочий агент)
    # "stub"   — заглушка, ничего не подбирает (стартовая точка)
    agent_type: str = "simple"

    # --- LLM через OpenRouter (OpenAI-совместимый API) ---
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    llm_model: str = "openai/gpt-4o-mini"
    vision_model: str = "openai/gpt-4o-mini"
    llm_temperature: float = 0.1
    llm_timeout_seconds: float = 30.0

    # --- Режим без ключей ---
    # true — не ходим в LLM/vision, работаем на эвристиках и заглушках.
    stub_llm: bool = True
    stub_vision: bool = True

    # --- RAG / база знаний по стилю ---
    knowledge_base_dir: str = "knowledge_base"
    rag_top_k: int = 3

    # --- Каталог и подбор ---
    catalog_snapshot: str = "data/catalog.json"
    default_budget_rub: int = 15000


@lru_cache
def get_settings() -> Settings:
    """Кэшируем настройки — читаем окружение один раз за жизнь процесса."""
    return Settings()
