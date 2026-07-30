"""Композиция образа — чистая функция подбора вещей по слотам.

Берёт список доступных вещей (уже отфильтрованных каталогом) и жадно собирает
образ: для каждого слота выбирает вещь с лучшим совпадением по вкусу и цвету, не
выходя за бюджет. Цветовой скоринг — упрощённая колористика (перенос из старого
`tools/color.py`): цвет оценивается под цветотип и палитру вкуса пользователя.

Никакого I/O: ни БД, ни сети — только вход -> Look. Легко тестируется.
"""

from __future__ import annotations

from app.agent.schemas import Appearance, Constraints, Item, Look, StyleProfile

# --- Цветовой скоринг -----------------------------------------------------

SEASON_COLORS: dict[str, set[str]] = {
    "зима": {"чёрный", "белый", "синий", "изумруд", "красный", "серый", "фуксия"},
    "лето": {"серо-голубой", "голубой", "синий", "лавандовый", "серый", "белый",
             "пудровый", "сиреневый"},
    "весна": {"бежевый", "коралловый", "персиковый", "золотистый", "мятный",
              "жёлтый", "тёплый зелёный"},
    "осень": {"хаки", "терракота", "терракотовый", "горчичный", "коричневый",
              "оливковый", "бежевый", "рыжий"},
}
WARM = {"коралловый", "персиковый", "золотистый", "горчичный", "терракота",
        "терракотовый", "рыжий", "бежевый", "коричневый", "хаки", "оливковый", "жёлтый"}
COOL = {"серо-голубой", "голубой", "синий", "лавандовый", "сиреневый", "изумруд",
        "фуксия", "пудровый"}
NEUTRALS = {"чёрный", "белый", "серый", "бежевый"}
_COOL_SEASONS = {"лето", "зима"}


def _tokens(color: str) -> set[str]:
    c = (color or "").strip().lower()
    parts = {c} | set(c.replace("-", " ").split())
    return {p for p in parts if p}


def _expand(colors: set[str]) -> set[str]:
    out: set[str] = set()
    for c in colors:
        out |= _tokens(c)
    return out


def make_scorer(color_type: str | None, palette: list[str] | None):
    """Скорер уместности цвета вещи под цветотип и палитру вкуса."""
    season_toks = _expand(SEASON_COLORS.get(color_type, set())) if color_type else set()
    palette_toks = _expand(set(palette)) if palette else set()
    cool_type = color_type in _COOL_SEASONS if color_type else False

    def score(item_color: str) -> float:
        toks = _tokens(item_color)
        s = 0.0
        if color_type:
            if toks & season_toks:
                s += 2.0
            if cool_type and (toks & WARM):
                s -= 1.5
            if (not cool_type) and (toks & COOL):
                s -= 1.5
        if toks & palette_toks:
            s += 3.0  # вкус пользователя весит больше приора цветотипа
        if toks & NEUTRALS:
            s += 0.3
        return s

    return score


# --- Сборка образа --------------------------------------------------------

# Повод -> предпочитаемые стилевые теги.
OCCASION_TAGS: dict[str, list[str]] = {
    "офис": ["офис", "smart-casual", "минимализм"],
    "свидание": ["smart-casual", "минимализм"],
    "прогулка": ["casual"],
    "вечеринка": ["вечер", "smart-casual"],
    "спорт": ["casual"],
}

BASE_SLOTS = ["верх", "низ", "обувь"]
_OUTER_SEASONS = {"деми", "осень", "зима"}


def occasion_tags(occasion: str | None) -> list[str]:
    return OCCASION_TAGS.get((occasion or "").lower(), [])


def _required_slots(constraints: Constraints) -> list[str]:
    slots = list(BASE_SLOTS)
    if (constraints.season or "").lower() in _OUTER_SEASONS:
        slots.append("верхняя одежда")
    return slots


def compose_look(
    items: list[Item],
    constraints: Constraints,
    appearance: Appearance,
    style_profile: StyleProfile,
    default_budget: int,
) -> Look:
    """Жадно собрать образ по слотам в рамках бюджета."""
    scorer = make_scorer(appearance.color_type, style_profile.palette)
    taste = set(style_profile.styles) | set(occasion_tags(constraints.occasion))
    budget = constraints.budget_rub or default_budget

    by_slot: dict[str, list[Item]] = {}
    for it in items:
        by_slot.setdefault(it.category, []).append(it)

    chosen: list[Item] = []
    total = 0
    for slot in _required_slots(constraints):
        cands = sorted(
            by_slot.get(slot, []),
            key=lambda it: (
                -len(taste & set(it.style_tags)),  # ближе к вкусу/поводу
                -scorer(it.color),                  # уместнее по цвету
                it.price,                           # дешевле
            ),
        )
        pick = next((c for c in cands if total + c.price <= budget), None)
        if pick is None and cands:
            pick = min(cands, key=lambda it: it.price)  # фолбэк: самое дешёвое
        if pick is not None:
            chosen.append(pick)
            total += pick.price

    # Один аксессуар, если остался бюджет — приятный, но не обязательный штрих.
    for acc in sorted(by_slot.get("аксессуар", []), key=lambda it: it.price):
        if total + acc.price <= budget:
            chosen.append(acc)
            total += acc.price
            break

    return Look(items=chosen, rationale=_rationale(chosen, constraints, appearance, total))


def _rationale(
    items: list[Item], constraints: Constraints, appearance: Appearance, total: int
) -> str:
    if not items:
        return "Под заданные ограничения ничего не удалось подобрать."
    parts = []
    if constraints.occasion:
        parts.append(f"повод — {constraints.occasion}")
    if appearance.color_type:
        parts.append(f"цвета под цветотип «{appearance.color_type}»")
    colors = ", ".join(dict.fromkeys(it.color for it in items if it.color))
    head = "Собрала образ"
    if parts:
        head += ": " + ", ".join(parts)
    return f"{head}. Палитра: {colors}. Итого {total} ₽."
