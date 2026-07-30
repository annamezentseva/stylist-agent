"""Контекстный бандит — обучение предпочтениям пользователя с подкреплением.

Это ОДНОШАГОВЫЙ RL: состояние = признаки товара, действие = «показать/выбрать»,
reward = реакция пользователя. Модель линейная (перцептрон-стайл онлайн-обновление):
    score(item) = w · features(item)
    w <- w + lr * (reward - score) * features
Без данных ведёт себя нейтрально (score=0 -> порядок не меняется). Учится per-user.

Почему бандит, а не полноценный (multi-agent) RL — см. ADR-002: нам не нужен
симулятор и совместные политики; нужен онлайн-реранк по разреженному фидбэку.
"""
from __future__ import annotations

from ..models import Item


def featurize(item: Item) -> dict[str, float]:
    feats: dict[str, float] = {}
    for t in item.style_tags:
        feats[f"style:{t}"] = 1.0
    feats[f"color:{item.color}"] = 1.0
    feats[f"brand:{item.brand}"] = 1.0
    feats[f"store:{item.store}"] = 1.0
    feats[f"cat:{item.category}"] = 1.0
    band = "budget" if item.price < 3000 else "mid" if item.price < 6000 else "premium"
    feats[f"price:{band}"] = 1.0
    return feats


class LinearBandit:
    def __init__(self, lr: float = 0.1) -> None:
        self.w: dict[str, float] = {}
        self.lr = lr

    def score(self, item: Item) -> float:
        return sum(self.w.get(k, 0.0) * v for k, v in featurize(item).items())

    def update(self, item: Item, reward: float) -> float:
        err = reward - self.score(item)
        for k, v in featurize(item).items():
            self.w[k] = self.w.get(k, 0.0) + self.lr * err * v
        return err

    def rerank(self, items: list[Item]) -> list[Item]:
        # Стабильная сортировка: при равных весах сохраняется исходный (ценовой) порядок.
        return sorted(items, key=self.score, reverse=True)


def train_from_feedback(items_by_id: dict[str, Item], feedback: list[dict], lr: float = 0.1) -> LinearBandit:
    b = LinearBandit(lr=lr)
    for ev in feedback:
        it = items_by_id.get(ev["item_id"])
        if it is not None:
            b.update(it, float(ev.get("reward", 0.0)))
    return b
