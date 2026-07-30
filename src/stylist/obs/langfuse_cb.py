"""Observability через LangFuse (v3/v4, интеграция langchain).

Возвращает CallbackHandler для передачи в config графа — сборка config
централизована в stylist.graph.run_config():
    app.invoke(state, config=run_config(get_langfuse_handler(), run_name=...))

В v3/v4 ключи задаются на клиенте Langfuse(...) (конфигурирует синглтон), а сам
CallbackHandler() создаётся без аргументов и подхватывает этот клиент. После
короткого прогона нужно вызвать flush_langfuse(), иначе события не успеют уйти.

ПРИВАТНОСТЬ: обеспечивается ЗДЕСЬ, на границе трейсинга — клиент создаётся с
mask=mask_photos, поэтому поле `photos` (пути/сырые ссылки на снимки) заменяется
счётчиками во всех отправляемых событиях. Узлам графа думать об этом не нужно.
"""
from __future__ import annotations

from ..config import settings


def mask_photos(data):
    """Заменить содержимое поля `photos` счётчиками во вложенных dict (для mask=)."""
    if not isinstance(data, dict):
        return data
    safe = {}
    for k, v in data.items():
        if k == "photos" and isinstance(v, dict):
            safe[k] = {kk: len(vv) if isinstance(vv, (list, tuple)) else "…" for kk, vv in v.items()}
        elif isinstance(v, dict):
            safe[k] = mask_photos(v)
        else:
            safe[k] = v
    return safe


def get_langfuse_handler():
    if not (settings.langfuse_public_key and settings.langfuse_secret_key):
        return None
    try:
        from langfuse import Langfuse
        from langfuse.langchain import CallbackHandler

        # Конфигурируем клиент-синглтон; mask= маскирует фото во ВСЕХ событиях.
        Langfuse(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            host=settings.langfuse_host,
            mask=mask_photos,
        )
        return CallbackHandler()
    except Exception:
        return None


def flush_langfuse() -> None:
    """Досылает буферизованные события в LangFuse (нужно после коротких прогонов)."""
    try:
        from langfuse import get_client

        get_client().flush()
    except Exception:
        pass
