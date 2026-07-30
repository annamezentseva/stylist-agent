"""Интерфейсы (абстракции) слоя агента — «розетки», в которые вставляются детали.

Ровно как в Workshop 1: сначала договариваемся о контрактах (LLM, ретривер,
каталог, vision, сам агент), а конкретные реализации — заглушка или боевой
режим — приходят потом и взаимозаменяемы. Верхний код зависит только от этих
абстрактных классов, а не от httpx, SQLAlchemy или OpenAI.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TypeVar

from pydantic import BaseModel

from app.agent.schemas import (
    Appearance,
    Item,
    RetrievedRule,
    StyleProfile,
    StylistRequest,
    StylistResult,
)

# Любая pydantic-модель, в которую валидируется структурный ответ LLM.
TModel = TypeVar("TModel", bound=BaseModel)


class LLM(ABC):
    """Языковая модель. Две операции: свободный текст и строгий JSON по схеме."""

    @abstractmethod
    async def complete(self, system: str, user: str) -> str:
        """Вернуть текстовый ответ модели."""

    @abstractmethod
    async def complete_structured(
        self, system: str, user: str, schema: type[TModel]
    ) -> TModel:
        """Вернуть ответ, провалидированный в pydantic-схему `schema`."""


class Retriever(ABC):
    """Поиск по базе знаний стиля (правила колористики, фигуры, дресс-кода)."""

    @abstractmethod
    async def search(self, query: str, top_k: int = 3) -> list[RetrievedRule]:
        """Найти самые релевантные правила под запрос."""


class Catalog(ABC):
    """Поиск вещей в каталоге под ограничения запроса."""

    @abstractmethod
    async def search(
        self,
        categories: list[str] | None = None,
        sizes: dict[str, str] | None = None,
        budget_rub: int | None = None,
        style_tags: list[str] | None = None,
        avoid: list[str] | None = None,
    ) -> list[Item]:
        """Отфильтровать доступные вещи и отсортировать по совпадению стиля/цене."""


class Vision(ABC):
    """Анализ фотографий: внешность и вкус по референсам."""

    @abstractmethod
    async def analyze_appearance(
        self, image_refs: list[str], hint: dict | None = None
    ) -> Appearance:
        """Фото тела/лица -> цветотип, подтон, контраст, тип фигуры."""

    @abstractmethod
    async def profile_taste(
        self, image_refs: list[str], hint: dict | None = None
    ) -> StyleProfile:
        """Фото-референсы нравящихся образов -> вектор вкуса."""


class Agent(ABC):
    """Сам агент-стилист. Один метод, как `Agent.handle` в Workshop 1."""

    @abstractmethod
    async def handle(self, request: StylistRequest) -> StylistResult:
        """Обработать запрос и вернуть решение (образ / совет / нужны данные)."""
