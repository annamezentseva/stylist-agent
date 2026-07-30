"""Сбор сигналов вознаграждения от пользователя (в БД).

Каждая реакция на образ/вещь (👍/👎/куплю/пропустить) — это reward для контекстного
бандита. Presenter/веб вешают кнопки, их нажатия попадают сюда.
"""
from __future__ import annotations

from ..db.repo import FeedbackRepo

# Награды сигналов (шкала для контекстного бандита).
REWARD = {"buy": 2.0, "like": 1.0, "skip": 0.0, "dislike": -1.0}


def record_feedback(user_id: str, item_id: str, signal: str, look_id: str | None = None) -> dict:
    return FeedbackRepo.add(user_id=user_id, item_id=item_id, signal=signal,
                            reward=REWARD.get(signal, 0.0), look_id=look_id)


def load_feedback(user_id: str | None = None) -> list[dict]:
    return FeedbackRepo.load(user_id=user_id)
