"""Доменные схемы агента-стилиста — строгий контракт входа/выхода.

Всё, что «течёт» через агента, описано здесь как pydantic-модели. Это аналог
`AgentRequest` / `AgentResult` из Workshop 1, только предметная область другая:
не тикеты поддержки, а образы одежды. API-слой и сервис знают только эти типы,
а не внутренности агента.
"""

from __future__ import annotations

import enum
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

# Слоты образа = категории каталога. Держим списком, чтобы валидация была честной.
Slot = Literal["верх", "низ", "обувь", "верхняя одежда", "аксессуар"]
ColorType = Literal["весна", "лето", "осень", "зима"]


class Appearance(BaseModel):
    """Внешность человека (из фото или подсказки). null = признак не определён."""

    color_type: Optional[ColorType] = None
    undertone: Optional[Literal["тёплый", "холодный", "нейтральный"]] = None
    contrast: Optional[Literal["низкий", "средний", "высокий"]] = None
    body_shape: Optional[str] = None
    face_shape: Optional[str] = None

    def is_known(self) -> bool:
        """Есть ли хоть что-то, на что опереться при подборе цвета."""
        return bool(self.color_type or self.undertone or self.contrast)


class StyleProfile(BaseModel):
    """Устойчивый вкус пользователя (из фото-референсов образов, которые нравятся)."""

    styles: list[str] = Field(default_factory=list)
    palette: list[str] = Field(default_factory=list)
    silhouettes: list[str] = Field(default_factory=list)
    likes: list[str] = Field(default_factory=list)
    dislikes: list[str] = Field(default_factory=list)

    def is_known(self) -> bool:
        return bool(self.styles or self.palette)


class Constraints(BaseModel):
    """Жёсткие ограничения запроса: повод, бюджет, размеры, чего избегать."""

    occasion: Optional[str] = None
    budget_rub: Optional[int] = None
    season: Optional[str] = None
    sizes: dict[str, str] = Field(default_factory=dict)  # {"верх": "M", "низ": "46"}
    avoid: list[str] = Field(default_factory=list)


class Item(BaseModel):
    """Одна вещь каталога. Совпадает по полям с ORM-моделью `Item`."""

    model_config = ConfigDict(from_attributes=True)  # можно собрать из ORM-строки

    id: str
    title: str
    brand: str = ""
    category: Slot
    color: str = ""
    price: int
    sizes: list[str] = Field(default_factory=list)
    style_tags: list[str] = Field(default_factory=list)
    in_stock: bool = True
    moscow_available: bool = True
    store: str = ""
    url: str = ""
    image_url: str = ""


class Look(BaseModel):
    """Собранный образ: набор вещей по слотам + объяснение подбора."""

    items: list[Item] = Field(default_factory=list)
    rationale: str = ""

    @property
    def total_price(self) -> int:
        return sum(it.price for it in self.items)

    @property
    def slots(self) -> list[str]:
        return [it.category for it in self.items]


class StylistAction(str, enum.Enum):
    """Что агент решил сделать — аналог ANSWER/ESCALATE из Workshop 1."""

    LOOK = "look"          # собрал готовый образ
    ADVICE = "advice"      # ответил советом по стилю (вопрос пользователя)
    NEED_INFO = "need_info"  # не хватает данных, нужно уточнение (эскалация)


class RetrievedRule(BaseModel):
    """Фрагмент базы знаний, найденный ретривером (для объяснений и советов)."""

    source: str
    text: str
    score: float = 0.0


class StylistRequest(BaseModel):
    """Вход агента: кто, что просит и что мы уже знаем о человеке."""

    user_id: str
    text: str
    intent: Optional[Literal["new_look", "refine", "question"]] = None
    photos: dict[str, list[str]] = Field(default_factory=dict)  # {"body": [...], "refs": [...]}
    appearance: Appearance = Field(default_factory=Appearance)
    style_profile: StyleProfile = Field(default_factory=StyleProfile)
    constraints: Constraints = Field(default_factory=Constraints)


class StylistResult(BaseModel):
    """Выход агента: решение + образ/ответ + чем оно обосновано.

    Дополнительно возвращаем обогащённый профиль (appearance/style_profile/
    constraints), чтобы сервисный слой мог его сохранить в БД.
    """

    action: StylistAction
    answer: str = ""
    look: Optional[Look] = None
    rationale: str = ""
    sources: list[str] = Field(default_factory=list)
    missing: list[str] = Field(default_factory=list)

    # Обновлённый профиль для персиста (заполняется агентом по ходу обработки).
    appearance: Optional[Appearance] = None
    style_profile: Optional[StyleProfile] = None
    constraints: Optional[Constraints] = None
