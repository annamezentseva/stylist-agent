"""Дельта-синхронизация каталога в БД: fetch -> diff -> upsert -> пометка новинок.

Идемпотентно. Новизна фиксируется полем first_seen. Пишет в общую БД (репозиторий),
поэтому результат виден сразу и Telegram, и вебу.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..db.repo import CatalogRepo
from .adapters import FeedAdapter


@dataclass
class SyncReport:
    added: list[str] = field(default_factory=list)
    updated: list[str] = field(default_factory=list)
    unchanged: int = 0

    def __str__(self) -> str:
        return (f"добавлено: {len(self.added)} {self.added}\n"
                f"обновлено: {len(self.updated)} {self.updated}\n"
                f"без изменений: {self.unchanged}")


def sync_catalog(adapters: list[FeedAdapter]) -> SyncReport:
    report = SyncReport()
    for adapter in adapters:
        for raw in adapter.fetch():
            rec = adapter.normalize(raw).model_dump()
            outcome = CatalogRepo.upsert(rec)
            if outcome == "added":
                report.added.append(rec["id"])
            elif outcome == "updated":
                report.updated.append(rec["id"])
            else:
                report.unchanged += 1
    return report


def new_arrivals(since_days: int = 7) -> list[dict]:
    """Товары, впервые появившиеся за последние since_days — для проактивных уведомлений."""
    return CatalogRepo.new_arrivals(since_days=since_days)
