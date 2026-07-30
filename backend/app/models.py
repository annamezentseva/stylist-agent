"""ORM-модели: всего три таблицы.

  * Item        — каталог вещей (что можно купить);
  * UserProfile — что мы знаем о пользователе (внешность, вкус, ограничения);
  * LookRecord  — история собранных образов и ответов агента.

Это вся база. Раньше сущностей было больше — для учебного проекта достаточно
этих трёх. Списки (размеры, теги, состав образа) храним в JSON-колонках:
работает и в SQLite, и в Postgres.
"""

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Item(Base):
    """Вещь каталога. id — строковый артикул из снимка каталога."""

    __tablename__ = "items"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    title: Mapped[str] = mapped_column(String(300))
    brand: Mapped[str] = mapped_column(String(100), default="")
    category: Mapped[str] = mapped_column(String(50), index=True)
    color: Mapped[str] = mapped_column(String(50), default="")
    price: Mapped[int] = mapped_column(Integer, index=True)
    sizes: Mapped[list] = mapped_column(JSON, default=list)
    style_tags: Mapped[list] = mapped_column(JSON, default=list)
    in_stock: Mapped[bool] = mapped_column(Boolean, default=True)
    moscow_available: Mapped[bool] = mapped_column(Boolean, default=True)
    store: Mapped[str] = mapped_column(String(100), default="")
    url: Mapped[str] = mapped_column(String(500), default="")
    image_url: Mapped[str] = mapped_column(String(500), default="")


class UserProfile(Base):
    """Профиль пользователя: внешность, вкус, постоянные ограничения."""

    __tablename__ = "user_profiles"

    user_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    appearance: Mapped[dict] = mapped_column(JSON, default=dict)
    style_profile: Mapped[dict] = mapped_column(JSON, default=dict)
    constraints: Mapped[dict] = mapped_column(JSON, default=dict)
    photos: Mapped[dict] = mapped_column(JSON, default=dict)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class LookRecord(Base):
    """История: что пользователь спросил и что агент ответил/собрал."""

    __tablename__ = "looks"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(String(100), index=True)
    request_text: Mapped[str] = mapped_column(Text)
    action: Mapped[str] = mapped_column(String(30))
    answer: Mapped[str] = mapped_column(Text, default="")
    rationale: Mapped[str] = mapped_column(Text, default="")
    # items — список вещей образа на момент подбора (снимок, а не ссылки).
    items: Mapped[list] = mapped_column(JSON, default=list)
    sources: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
