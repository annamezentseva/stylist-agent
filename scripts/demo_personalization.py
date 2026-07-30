"""Демо контекстного бандита: как фидбэк меняет ранжирование выдачи.

    PYTHONPATH=src python scripts/demo_personalization.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from stylist.models import Item  # noqa: E402
from stylist.personalization.bandit import train_from_feedback  # noqa: E402
from stylist.personalization.feedback import REWARD  # noqa: E402


def main() -> None:
    catalog = json.loads((ROOT / "data" / "catalog_snapshot.sample.json").read_text(encoding="utf-8"))
    items = [Item(**i) for i in catalog if i["category"] == "верх"]
    by_id = {i.id: i for i in items}

    print("Кандидаты (верх) до обучения — порядок по цене:")
    for it in sorted(items, key=lambda x: x.price):
        print(f"  {it.price:>5}₽  {it.title}  [{', '.join(it.style_tags)}]")

    # Пользователь любит чёрное/минимализм, не любит синее.
    feedback = [
        {"item_id": "top-black-tshirt", "reward": REWARD["buy"]},
        {"item_id": "top-black-tshirt", "reward": REWARD["like"]},
        {"item_id": "top-blue-blouse", "reward": REWARD["dislike"]},
    ]
    bandit = train_from_feedback(by_id, feedback)

    print("\nПосле обучения на фидбэке (👍 чёрное/минимализм, 👎 синее) — порядок по предпочтению:")
    for it in bandit.rerank(items):
        print(f"  score={bandit.score(it):+.2f}  {it.title}  [{', '.join(it.style_tags)}]")


if __name__ == "__main__":
    main()
