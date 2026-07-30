"""Типизированные схемы домена (Pydantic v2).

Структурный вывод — сквозной приём проекта: vision- и text-узлы отдают
эти модели, а eval-ассерты проверяют именно типизированные поля.
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

Slot = Literal["верх", "низ", "обувь", "верхняя одежда", "аксессуар"]
ColorType = Literal["весна", "лето", "осень", "зима"]


class Appearance(BaseModel):
    """Результат анализа фото внешности."""
    color_type: Optional[ColorType] = None
    undertone: Optional[Literal["тёплый", "холодный", "нейтральный"]] = None
    contrast: Optional[Literal["низкий", "средний", "высокий"]] = None
    body_shape: Optional[str] = None
    face_shape: Optional[str] = None

    def is_complete(self) -> bool:
        return self.color_type is not None and self.body_shape is not None


class StyleProfile(BaseModel):
    """Вектор вкуса, извлечённый из фото-референсов (обязательный этап)."""
    styles: list[str] = Field(default_factory=list)
    palette: list[str] = Field(default_factory=list)
    silhouettes: list[str] = Field(default_factory=list)
    likes: list[str] = Field(default_factory=list)
    dislikes: list[str] = Field(default_factory=list)

    def is_complete(self) -> bool:
        return bool(self.styles or self.palette)


class Constraints(BaseModel):
    """Явные ограничения запроса."""
    occasion: Optional[str] = None
    budget_rub: Optional[int] = None
    sizes: dict[str, str] = Field(default_factory=dict)  # slot -> размер
    season: Optional[str] = None
    must_have: list[str] = Field(default_factory=list)
    avoid: list[str] = Field(default_factory=list)

    def is_complete(self) -> bool:
        return self.occasion is not None and self.budget_rub is not None and bool(self.sizes)


class Item(BaseModel):
    """Товар из каталога московских магазинов."""
    id: str
    title: str
    brand: str
    category: Slot
    color: str
    price: int
    sizes: list[str] = Field(default_factory=list)
    style_tags: list[str] = Field(default_factory=list)
    in_stock: bool = True
    moscow_available: bool = True
    store: str = ""
    url: str = ""
    image_url: str = ""
    first_seen: Optional[str] = None  # проставляется дельта-синхронизацией каталога


class Look(BaseModel):
    """Собранный образ."""
    items: list[Item] = Field(default_factory=list)
    rationale: str = ""

    @property
    def total_price(self) -> int:
        return sum(i.price for i in self.items)

    @property
    def slots(self) -> set[str]:
        return {i.category for i in self.items}


class Critique(BaseModel):
    """Вердикт критика: программные проверки + оценка судьи."""
    verdict: Literal["approve", "reject"] = "reject"
    issues: list[str] = Field(default_factory=list)
    judge_score: Optional[float] = None
    lessons: list[str] = Field(default_factory=list)  # Reflexion: «урок» для повторной сборки
