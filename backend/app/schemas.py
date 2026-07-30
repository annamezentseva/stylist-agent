"""Pydantic-схемы HTTP-слоя (то, что летает по API).

Важно разделять:
  * схемы API (здесь)                        — контракт с фронтендом;
  * доменные схемы агента (agent/schemas.py) — контракт внутри агента.
Так слои не протекают друг в друга.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.agent.schemas import Appearance, Constraints, Item, StyleProfile


# --- Вход от пользователя ---


class StylistRequestIn(BaseModel):
    """Запрос к стилисту: текст + опционально фото и ограничения."""

    user_id: str = Field(default="demo", max_length=100)
    text: str = Field(min_length=1, max_length=2000)
    photos: dict[str, list[str]] = Field(default_factory=dict)
    constraints: Constraints = Field(default_factory=Constraints)


class ProfileIn(BaseModel):
    """Ручное сохранение профиля (если пользователь заполняет анкету сам)."""

    appearance: Appearance = Field(default_factory=Appearance)
    style_profile: StyleProfile = Field(default_factory=StyleProfile)
    constraints: Constraints = Field(default_factory=Constraints)


# --- Ответы наружу ---


class LookOut(BaseModel):
    """Результат работы агента для фронтенда."""

    id: int | None = None
    action: str
    answer: str = ""
    items: list[Item] = Field(default_factory=list)
    rationale: str = ""
    sources: list[str] = Field(default_factory=list)
    missing: list[str] = Field(default_factory=list)
    total_price: int = 0


class LookSummary(BaseModel):
    """Короткая карточка образа для истории."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    request_text: str
    action: str
    created_at: datetime


class ProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: str
    appearance: dict = Field(default_factory=dict)
    style_profile: dict = Field(default_factory=dict)
    constraints: dict = Field(default_factory=dict)
