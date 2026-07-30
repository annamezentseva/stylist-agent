"""ORM-таблицы: каталог, фидбэк, профиль пользователя.

Раньше это были локальные файлы (catalog.json, feedback.jsonl). Теперь — общая БД,
чтобы Telegram и веб видели одно состояние, а sync-воркер писал в него же.
"""
from __future__ import annotations

import datetime as dt

from sqlalchemy import JSON, Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .session import Base


class ItemORM(Base):
    __tablename__ = "items"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    title: Mapped[str] = mapped_column(String)
    brand: Mapped[str] = mapped_column(String, default="")
    category: Mapped[str] = mapped_column(String, index=True)
    color: Mapped[str] = mapped_column(String, default="")
    price: Mapped[int] = mapped_column(Integer, index=True)
    sizes: Mapped[list] = mapped_column(JSON, default=list)
    style_tags: Mapped[list] = mapped_column(JSON, default=list)
    in_stock: Mapped[bool] = mapped_column(Boolean, default=True)
    moscow_available: Mapped[bool] = mapped_column(Boolean, default=True)
    store: Mapped[str] = mapped_column(String, default="")
    url: Mapped[str] = mapped_column(String, default="")
    image_url: Mapped[str] = mapped_column(String, default="")
    first_seen: Mapped[str | None] = mapped_column(String, nullable=True)
    content_hash: Mapped[str | None] = mapped_column(String, nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id, "title": self.title, "brand": self.brand,
            "category": self.category, "color": self.color, "price": self.price,
            "sizes": self.sizes or [], "style_tags": self.style_tags or [],
            "in_stock": self.in_stock, "moscow_available": self.moscow_available,
            "store": self.store, "url": self.url, "image_url": self.image_url,
            "first_seen": self.first_seen,
        }


class FeedbackORM(Base):
    __tablename__ = "feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)
    user_id: Mapped[str] = mapped_column(String, index=True)
    item_id: Mapped[str] = mapped_column(String, index=True)
    look_id: Mapped[str | None] = mapped_column(String, nullable=True)
    signal: Mapped[str] = mapped_column(String)
    reward: Mapped[float] = mapped_column(default=0.0)


class UserProfileORM(Base):
    __tablename__ = "user_profiles"

    user_id: Mapped[str] = mapped_column(String, primary_key=True)
    appearance: Mapped[dict] = mapped_column(JSON, default=dict)
    style_profile: Mapped[dict] = mapped_column(JSON, default=dict)
    constraints: Mapped[dict] = mapped_column(JSON, default=dict)
    photos: Mapped[dict] = mapped_column(JSON, default=dict)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)
