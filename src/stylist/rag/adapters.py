"""Адаптеры магазинов: единый контракт fetch()->raw, normalize(raw)->Item.

Каждый магазин = свой адаптер. Дельта-синхронизация работает поверх любого набора
адаптеров, не зная деталей конкретного источника (тот же приём, что и в tools/catalog).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol, runtime_checkable

from ..models import Item


@runtime_checkable
class FeedAdapter(Protocol):
    store: str

    def fetch(self) -> list[dict]: ...
    def normalize(self, raw: dict) -> Item: ...


class SampleFeedAdapter:
    """Читает локальный JSON-фид (список товаров). Для оффлайн-демо, тестов и сидов."""

    def __init__(self, path: str | Path, store: str = "Sample") -> None:
        self.path = Path(path)
        self.store = store

    def fetch(self) -> list[dict]:
        return json.loads(self.path.read_text(encoding="utf-8"))

    def normalize(self, raw: dict) -> Item:
        data = dict(raw)
        data.setdefault("store", self.store)
        return Item(**{k: data[k] for k in Item.model_fields if k in data})


class YMLFeedAdapter:
    """YML-прайслист (формат Яндекс Маркета). Реализуется под конкретный магазин.

    fetch(): скачать XML -> распарсить <offer> -> список словарей.
    normalize(): смэппить поля offer (name, price, param 'Размер', picture, url,
    available) в схему Item.
    """

    def __init__(self, url: str, store: str) -> None:
        self.url = url
        self.store = store

    def fetch(self) -> list[dict]:  # pragma: no cover - точка расширения
        raise NotImplementedError(
            "YMLFeedAdapter: подключите загрузку YML (requests.get(url) -> ElementTree -> offers)."
        )

    def normalize(self, raw: dict) -> Item:  # pragma: no cover
        raise NotImplementedError


class CPAFeedAdapter:
    """Товарный фид партнёрской сети (Admitad/ePN/Advcake): CSV/XML с ценой,
    наличием и партнёрской ссылкой (deeplink). Легальный способ выкачки каталога.
    """

    def __init__(self, url: str, store: str) -> None:
        self.url = url
        self.store = store

    def fetch(self) -> list[dict]:  # pragma: no cover - точка расширения
        raise NotImplementedError("CPAFeedAdapter: подключите выгрузку фида партнёрской сети.")

    def normalize(self, raw: dict) -> Item:  # pragma: no cover
        raise NotImplementedError
