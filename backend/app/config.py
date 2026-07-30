"""Конфигурация приложения.

Все настройки читаются из переменных окружения (.env). Один источник правды,
типизированный и провалидированный через pydantic-settings. Никаких «магических»
строк по коду — только `get_settings()`.
"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# .env ищем и рядом с backend, и в корне проекта — чтобы приложение работало
# независимо от того, откуда его запустили.
_BACKEND_DIR = Path(__file__).resolve().parent.parent
_ENV_FILES = (_BACKEND_DIR.parent / ".env", _BACKEND_DIR / ".env")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=_ENV_FILES, extra="ignore")

    # --- База данных ---
    # По умолчанию SQLite-файл рядом с backend: ничего поднимать не нужно.
    database_url: str = f"sqlite+aiosqlite:///{_BACKEND_DIR / 'stylist.db'}"

    # --- Выбор реализации агента ---
    # "simple" — RAG + каталог + композиция образа (рабочий агент)
    # "stub"   — заглушка, ничего не подбирает (стартовая точка)
    agent_type: str = "simple"

    # --- LLM (любой OpenAI-совместимый провайдер) ---
    # По умолчанию — OpenAI. Для OpenRouter замените llm_base_url на
    # https://openrouter.ai/api/v1 и подставьте его ключ.
    llm_api_key: str = ""
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o-mini"
    llm_temperature: float = 0.1
    llm_timeout_seconds: float = 30.0

    # --- Vision (анализ фото). Если ключ пуст — берём общий llm_api_key. ---
    vision_api_key: str = ""
    vision_model: str = "gpt-4o-mini"

    # --- Режим без ключей ---
    # true — не ходим в LLM/vision, работаем на эвристиках и заглушках.
    stub_llm: bool = True
    stub_vision: bool = True

    # --- RAG / база знаний по стилю ---
    knowledge_base_dir: str = str(_BACKEND_DIR / "knowledge_base")
    rag_top_k: int = 3

    # --- Каталог и подбор ---
    catalog_snapshot: str = str(_BACKEND_DIR / "data" / "catalog.json")
    default_budget_rub: int = 15000

    @property
    def vision_key(self) -> str:
        """Ключ для vision: отдельный, если задан, иначе общий."""
        return self.vision_api_key or self.llm_api_key


@lru_cache
def get_settings() -> Settings:
    """Кэшируем настройки — читаем окружение один раз за жизнь процесса."""
    return Settings()
