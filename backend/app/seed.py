"""Наполнение каталога из JSON-снимка при старте.

Каталог — это данные, а не код: лежит в `data/catalog.json` обычным списком
объектов. При старте, если таблица пуста, вещи заливаются в БД. Чтобы добавить
товары, достаточно отредактировать JSON и удалить файл базы.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from sqlalchemy import func, select

from app.database import SessionLocal
from app.models import Item

logger = logging.getLogger(__name__)


async def seed_catalog(snapshot_path: str | Path) -> int:
    """Залить каталог, если таблица пуста. Возвращает число добавленных вещей."""
    path = Path(snapshot_path)
    if not path.exists():
        logger.warning("Catalog snapshot not found: %s", path)
        return 0

    async with SessionLocal() as session:
        count = await session.scalar(select(func.count()).select_from(Item))
        if count:
            logger.info("Catalog already filled: %s items", count)
            return 0

        records = json.loads(path.read_text(encoding="utf-8"))
        for rec in records:
            session.add(Item(**rec))
        await session.commit()

    logger.info("Catalog seeded: %s items from %s", len(records), path)
    return len(records)
