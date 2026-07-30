"""Инкрементальное обновление каталога в БД — запускается по расписанию (cron/launchd).

Демо (из корня проекта):
    PYTHONPATH=src python scripts/sync_catalog.py

  1) при пустой БД инициализирует каталог из снимка (полный импорт);
  2) применяет свежий фид магазина (delta_feed) -> добавляет новинки, обновляет
     изменившиеся товары, остальные не трогает;
  3) печатает отчёт и список новинок за 7 дней.

Повторный запуск идемпотентен. Сброс демо: rm data/stylist.db
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from stylist.config import settings  # noqa: E402
from stylist.db.repo import CatalogRepo  # noqa: E402
from stylist.rag.adapters import SampleFeedAdapter  # noqa: E402
from stylist.rag.sync import new_arrivals, sync_catalog  # noqa: E402


def main() -> None:
    seeded = CatalogRepo.seed_if_empty(settings.snapshot_path)
    if seeded:
        print(f"[init] импортировано товаров: {seeded}")

    stores = [
        SampleFeedAdapter(ROOT / "data" / "feeds" / "delta_feed.json", store="DemoStore"),
        # YMLFeedAdapter("https://shop.example/yml", store="МойМагазин"),
        # CPAFeedAdapter("https://cpa.example/feed.csv", store="Lamoda"),
    ]
    report = sync_catalog(stores)
    print("[sync]")
    print(report)
    print(f"[новинки за 7 дней] {[i['id'] for i in new_arrivals(since_days=7)]}")


if __name__ == "__main__":
    main()
