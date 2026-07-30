"""Инструменты каталога — ВНЕШНИЙ слой данных.

Каталог живёт в БД (репозиторий). Автосидинг из снимка при пустой таблице →
локальный запуск и бенчмарк работают без ручных шагов. Гибрид: CATALOG_MODE=live —
точка расширения под API маркетплейса. Граф вызывает функции одинаково.
"""
from __future__ import annotations

from ..config import settings
from ..db.repo import CatalogRepo

REQUIRED_SLOTS = ("верх", "низ", "обувь")
# Дефолтные размеры по слотам (когда пользователь их не назвал) — единый источник
# для preference_dialog и демо-скриптов; ключи обязаны совпадать с REQUIRED_SLOTS.
DEFAULT_SIZES = {"верх": "M", "низ": "46", "обувь": "41"}


def _ensure_seeded() -> None:
    CatalogRepo.seed_if_empty(settings.snapshot_path)


def search_catalog(
    categories: list[str] | None = None,
    sizes: dict[str, str] | None = None,
    budget_rub: int | None = None,
    style_tags: list[str] | None = None,
    avoid: list[str] | None = None,
) -> list[dict]:
    """Поиск товаров с фильтрами: категория, размер, бюджет-на-вещь, стиль, доступность в Москве."""
    _ensure_seeded()
    return CatalogRepo.search(categories=categories, sizes=sizes, budget_rub=budget_rub,
                              style_tags=style_tags, avoid=avoid)


def check_availability(item_id: str, size: str | None = None) -> dict:
    """Верификация наличия/размера/цены на момент выдачи (freshness)."""
    _ensure_seeded()
    it = CatalogRepo.get(item_id)
    if it is None:
        return {"item_id": item_id, "available": False, "price": None}
    available = bool(it["in_stock"] and it["moscow_available"])
    if size is not None:
        available = available and size in it.get("sizes", [])
    return {"item_id": item_id, "available": available, "price": it["price"]}
