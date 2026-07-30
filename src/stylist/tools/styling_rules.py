"""RAG-инструмент по базе знаний стиля.

Локальный retrieval (не внешний): правила загружаются из
data/knowledge_base/styling_rules.json (69 операционализированных правил:
колористика, тональный метод, схемы сочетаний, фигуры, иллюзии, капсула,
дресс-коды, стилевая согласованность, трендовые приёмы). Поиск — по пересечению
токенов запроса с тегами правила; в проде заменяется на векторный индекс.

Принцип власти правил (см. description базы): правила — скоринг и словарь
объяснений, НЕ вето; вкус пользователя из референсов перекрывает мягкие приоры.
"""
from __future__ import annotations

import json
from functools import lru_cache

from ..config import ROOT

_RULES_PATH = ROOT / "data" / "knowledge_base" / "styling_rules.json"

# Минимальный встроенный фолбэк (если файл базы недоступен).
_BUILTIN: list[dict] = [
    {"tags": ["зима", "цветотип", "палитра"],
     "text": "Зимнему цветотипу идут чистые холодные и контрастные цвета: чёрный, белый, изумруд, синий."},
    {"tags": ["лето", "цветотип", "палитра"],
     "text": "Летнему цветотипу — приглушённые холодные тона: серо-голубой, лавандовый, пудровый."},
    {"tags": ["капсула", "гардероб"],
     "text": "Капсула: 1 низ сочетается минимум с 3 верхами; база нейтральна, акцент — в аксессуарах."},
]


@lru_cache(maxsize=1)
def _load_rules() -> list[dict]:
    try:
        data = json.loads(_RULES_PATH.read_text(encoding="utf-8"))
        rules = [r for r in data.get("rules", []) if "rag" in r.get("consumers", ["rag"])]
        return rules or _BUILTIN
    except Exception:
        return _BUILTIN


def retrieve_styling_rules(query: str, k: int = 3) -> list[str]:
    """Топ-k правил по пересечению токенов запроса с тегами (наивный retrieval)."""
    rules = _load_rules()
    q = set(query.lower().replace(",", " ").replace("?", " ").split())
    scored = [(len(q & set(r["tags"])), r["text"]) for r in rules]
    scored = [t for t in scored if t[0] > 0] or [(0, r["text"]) for r in rules[:k]]
    scored.sort(key=lambda x: -x[0])
    return [text for _, text in scored[:k]]
