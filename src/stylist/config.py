"""Конфигурация приложения.

Читаем настройки из окружения через stdlib (без лишних зависимостей),
чтобы оффлайн-прогон бенчмарка работал даже без установленного pydantic-settings.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# Подхватываем .env из корня проекта ДО чтения переменных ниже (мягко, если dotenv не стоит).
try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
except Exception:
    pass


def _flag(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    # Каталог: "snapshot" (замороженный файл) или "live" (API маркетплейса).
    catalog_mode: str = os.getenv("CATALOG_MODE", "snapshot")
    snapshot_path: Path = Path(os.getenv("SNAPSHOT_PATH", str(ROOT / "data" / "catalog_snapshot.sample.json")))

    # STUB-режим: LLM/vision-узлы работают на детерминированных заглушках.
    # Так граф и бенчмарк запускаются без ключей и оплаты токенов.
    stub_llm: bool = _flag("STUB_LLM", True)

    # Облачный vision-API (используется, когда STUB_LLM=false).
    vision_api_key: str = os.getenv("VISION_API_KEY", "")
    vision_model: str = os.getenv("VISION_MODEL", "gpt-4o-mini")

    # Оркестрация/composer/judge.
    llm_api_key: str = os.getenv("LLM_API_KEY", "")
    llm_model: str = os.getenv("LLM_MODEL", "gpt-4o-mini")

    # Петля самокоррекции critic -> retriever.
    max_iterations: int = int(os.getenv("MAX_ITERATIONS", "2"))

    # Сколько раз gate может дёрнуть один сборщик профиля, прежде чем идти дальше
    # (защита от зацикливания, если vision вернул неполные атрибуты). 1 = одна попытка.
    max_gate_tries: int = int(os.getenv("MAX_GATE_TRIES", "1"))

    # Жёсткий потолок шагов графа LangGraph (страховка от бесконечных циклов).
    recursion_limit: int = int(os.getenv("RECURSION_LIMIT", "50"))

    # Персонализация: реранк выдачи контекстным бандитом по фидбэку пользователя.
    # По умолчанию выключено, чтобы бенчмарк оставался детерминированным.
    personalization: bool = _flag("PERSONALIZATION", False)

    # Telegram / LangFuse.
    telegram_token: str = os.getenv("TELEGRAM_TOKEN", "")
    langfuse_public_key: str = os.getenv("LANGFUSE_PUBLIC_KEY", "")
    langfuse_secret_key: str = os.getenv("LANGFUSE_SECRET_KEY", "")
    langfuse_host: str = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")

    # Хранилище состояния: локально SQLite, в проде Postgres (через DATABASE_URL).
    database_url: str = os.getenv("DATABASE_URL", f"sqlite:///{ROOT / 'data' / 'stylist.db'}")

    # Backend API.
    api_url: str = os.getenv("API_URL", "http://localhost:8000")  # адрес API для клиентов (бот)
    api_token: str = os.getenv("API_TOKEN", "")                    # секрет для защиты API (пусто = без проверки)
    upload_dir: Path = Path(os.getenv("UPLOAD_DIR", str(ROOT / "data" / "uploads")))

    # Единственный пользователь (режим «без входа»).
    default_user_id: str = os.getenv("DEFAULT_USER_ID", "me")


settings = Settings()
