"""Репозитории поверх ORM: каталог, фидбэк, профиль.

Инкапсулируют SQL, отдают простые dict/list — граф и API не знают про SQLAlchemy.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
from pathlib import Path

from sqlalchemy import func, select

from .models import FeedbackORM, ItemORM, UserProfileORM
from .session import init_db, session_scope


def content_hash(rec: dict) -> str:
    key = "|".join(str(rec.get(k)) for k in ("price", "in_stock", "moscow_available", "title"))
    key += "|" + ",".join(sorted(rec.get("sizes", [])))
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


class CatalogRepo:
    """Каталог товаров в БД. Автосидинг из снимка, если таблица пуста."""

    @staticmethod
    def count() -> int:
        with session_scope() as s:
            return s.scalar(select(func.count()).select_from(ItemORM)) or 0

    @staticmethod
    def seed_if_empty(snapshot_path: str | Path) -> int:
        init_db()
        if CatalogRepo.count() > 0:
            return 0
        raw = json.loads(Path(snapshot_path).read_text(encoding="utf-8"))
        now = dt.datetime.utcnow().isoformat(timespec="seconds")
        for rec in raw:
            CatalogRepo.upsert(rec, now=now)
        return len(raw)

    @staticmethod
    def upsert(rec: dict, now: str | None = None) -> str:
        """Возвращает 'added' | 'updated' | 'unchanged'."""
        now = now or dt.datetime.utcnow().isoformat(timespec="seconds")
        h = content_hash(rec)
        with session_scope() as s:
            row = s.get(ItemORM, rec["id"])
            if row is None:
                s.add(ItemORM(
                    id=rec["id"], title=rec["title"], brand=rec.get("brand", ""),
                    category=rec["category"], color=rec.get("color", ""), price=rec["price"],
                    sizes=rec.get("sizes", []), style_tags=rec.get("style_tags", []),
                    in_stock=rec.get("in_stock", True), moscow_available=rec.get("moscow_available", True),
                    store=rec.get("store", ""), url=rec.get("url", ""), image_url=rec.get("image_url", ""),
                    first_seen=now, content_hash=h,
                ))
                return "added"
            if row.content_hash == h:
                return "unchanged"
            row.title, row.price = rec["title"], rec["price"]
            row.sizes, row.in_stock = rec.get("sizes", []), rec.get("in_stock", True)
            row.moscow_available = rec.get("moscow_available", True)
            row.style_tags = rec.get("style_tags", row.style_tags)
            row.content_hash = h
            return "updated"

    @staticmethod
    def search(categories=None, sizes=None, budget_rub=None, style_tags=None, avoid=None) -> list[dict]:
        sizes = sizes or {}
        avoid = [a.lower() for a in (avoid or [])]
        tags = set(style_tags or [])

        stmt = select(ItemORM).where(ItemORM.in_stock.is_(True), ItemORM.moscow_available.is_(True))
        if categories:
            stmt = stmt.where(ItemORM.category.in_(categories))
        if budget_rub is not None:
            stmt = stmt.where(ItemORM.price <= budget_rub)

        with session_scope() as s:
            rows = [r.to_dict() for r in s.scalars(stmt).all()]

        out = []
        for it in rows:
            need = sizes.get(it["category"])
            if need and need not in it.get("sizes", []):
                continue
            haystack = (it["title"] + " " + it["color"] + " " + " ".join(it.get("style_tags", []))).lower()
            if any(a in haystack for a in avoid):
                continue
            out.append(it)
        out.sort(key=lambda it: (-len(tags & set(it.get("style_tags", []))), it["price"]))
        return out

    @staticmethod
    def get(item_id: str) -> dict | None:
        with session_scope() as s:
            row = s.get(ItemORM, item_id)
            return row.to_dict() if row else None

    @staticmethod
    def new_arrivals(since_days: int = 7) -> list[dict]:
        cutoff = (dt.datetime.utcnow() - dt.timedelta(days=since_days)).isoformat(timespec="seconds")
        with session_scope() as s:
            rows = s.scalars(select(ItemORM).where(ItemORM.first_seen >= cutoff)).all()
            return [r.to_dict() for r in rows]


class FeedbackRepo:
    @staticmethod
    def add(user_id: str, item_id: str, signal: str, reward: float, look_id: str | None = None) -> dict:
        init_db()
        with session_scope() as s:
            row = FeedbackORM(user_id=user_id, item_id=item_id, signal=signal,
                              reward=reward, look_id=look_id)
            s.add(row)
        return {"user_id": user_id, "item_id": item_id, "signal": signal, "reward": reward}

    @staticmethod
    def load(user_id: str | None = None) -> list[dict]:
        with session_scope() as s:
            stmt = select(FeedbackORM)
            if user_id is not None:
                stmt = stmt.where(FeedbackORM.user_id == user_id)
            return [{"user_id": r.user_id, "item_id": r.item_id, "signal": r.signal,
                     "reward": r.reward, "look_id": r.look_id} for r in s.scalars(stmt).all()]


class ProfileRepo:
    @staticmethod
    def get(user_id: str) -> dict:
        with session_scope() as s:
            row = s.get(UserProfileORM, user_id)
            if not row:
                return {}
            return {"appearance": row.appearance or {}, "style_profile": row.style_profile or {},
                    "constraints": row.constraints or {}, "photos": row.photos or {}}

    @staticmethod
    def save(user_id: str, appearance=None, style_profile=None, constraints=None, photos=None) -> None:
        init_db()
        with session_scope() as s:
            row = s.get(UserProfileORM, user_id)
            if row is None:
                row = UserProfileORM(user_id=user_id)
                s.add(row)
            if appearance is not None:
                row.appearance = appearance
            if style_profile is not None:
                row.style_profile = style_profile
            if constraints is not None:
                row.constraints = constraints
            if photos is not None:
                row.photos = photos
            row.updated_at = dt.datetime.utcnow()
