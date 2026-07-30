"""Файловый инструмент: сборка карточки/коллажа образа и запись на диск.

В скелете пишем JSON-манифест образа (без внешних зависимостей). В проде здесь
Pillow собирает картинку-коллаж из image_url вещей.
"""
from __future__ import annotations

import json
from pathlib import Path

from ..config import ROOT

OUT_DIR = ROOT / "data" / "looks"


def save_look_collage(look: dict, name: str) -> str:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / f"{name}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(look, f, ensure_ascii=False, indent=2)
    return str(path)
