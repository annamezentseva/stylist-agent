"""Каталог вещей поверх БД — реализация интерфейса `Catalog`.

Инкапсулирует SQL: фильтрует доступные вещи (в наличии + Москва) по категориям,
размеру, бюджету и стоп-словам, сортирует по совпадению стиля и цене. Наружу
отдаёт доменные `Item` — агент про SQLAlchemy ничего не знает.
"""

from __future__ import annotations

from sqlalchemy import select

from app.agent.base import Catalog
from app.agent.schemas import Item
from app.database import SessionLocal
from app.models import Item as ItemORM


class DbCatalog(Catalog):
    async def search(
        self,
        categories: list[str] | None = None,
        sizes: dict[str, str] | None = None,
        budget_rub: int | None = None,
        style_tags: list[str] | None = None,
        avoid: list[str] | None = None,
    ) -> list[Item]:
        sizes = sizes or {}
        avoid = [a.lower() for a in (avoid or [])]
        tags = set(style_tags or [])

        stmt = select(ItemORM).where(
            ItemORM.in_stock.is_(True), ItemORM.moscow_available.is_(True)
        )
        if categories:
            stmt = stmt.where(ItemORM.category.in_(categories))
        if budget_rub is not None:
            stmt = stmt.where(ItemORM.price <= budget_rub)

        async with SessionLocal() as session:
            rows = (await session.scalars(stmt)).all()

        out: list[Item] = []
        for r in rows:
            # Размер отфильтровать в SQL сложно (список в JSON) — проверяем в Python.
            need = sizes.get(r.category)
            if need and need not in (r.sizes or []):
                continue
            haystack = (r.title + " " + r.color + " " + " ".join(r.style_tags or [])).lower()
            if any(a in haystack for a in avoid):
                continue
            out.append(Item.model_validate(r))

        # Сначала — максимум совпадений по стилю, при равенстве дешевле.
        out.sort(key=lambda it: (-len(tags & set(it.style_tags)), it.price))
        return out
