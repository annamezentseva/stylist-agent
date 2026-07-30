"""Узлы графа. Каждый узел принимает состояние и возвращает частичный апдейт.

Разделение труда:
- Детерминированные узлы (retriever, composer, critic-программная-часть, presenter)
  реализованы «по-настоящему» -> благодаря этому eval'ы проверяют реальную логику.
- LLM/vision-узлы (router-инференс, analyzer, taste, judge) работают на заглушках
  в STUB-режиме; точки реального вызова помечены TODO.
"""
from __future__ import annotations

from ..config import settings
from ..models import Appearance, Constraints, Critique, Item, Look, StyleProfile
from ..tools.catalog import DEFAULT_SIZES, REQUIRED_SLOTS, check_availability, search_catalog
from ..tools.collage import save_look_collage
from ..tools.color import make_scorer
from ..tools.styling_rules import retrieve_styling_rules
from ..tools.vision import analyze_appearance, profile_taste


def _log(state: dict, tool: str, args: dict, ok: bool = True) -> list[dict]:
    """Журналируем вызов инструмента для eval «корректность tool-call»."""
    calls = list(state.get("tool_calls", []))
    calls.append({"tool": tool, "args": args, "ok": ok})
    return calls


def _hint(state: dict, key: str) -> dict:
    return (state.get("hints") or {}).get(key, {})


def _bump(state: dict, key: str) -> dict:
    """Инкремент счётчика попыток сборщика профиля (лимит в route_from_gate)."""
    tries = dict(state.get("gate_tries", {}))
    tries[key] = tries.get(key, 0) + 1
    return tries


# --- Точка ветвления №1: интент ------------------------------------------------

def router(state: dict) -> dict:
    intent = state.get("intent")
    text = state.get("request") or ""
    upd: dict = {}

    # Боевой режим: LLM понимает интент И достаёт ограничения (повод/бюджет/avoid)
    # из текста — даже если интент уже задан кнопкой клиента.
    if not settings.stub_llm and text.strip():
        try:
            from ..tools.nlu import understand_request

            nlu = understand_request(text)
            merged = dict(state.get("constraints", {}))
            for field in ("occasion", "budget_rub", "season"):
                value = getattr(nlu, field)
                if value is not None:
                    merged[field] = value  # свежая фраза пользователя главнее сохранённого
            if nlu.avoid:
                merged["avoid"] = nlu.avoid
            upd["constraints"] = merged
            upd["tool_calls"] = _log(state, "understand_request", nlu.model_dump())
            if not intent:
                intent = nlu.intent
                # Фото без анализа внешности — сперва разбор фото (как в эвристике).
                if intent == "new_look" and state.get("photos") and not state.get("appearance"):
                    intent = "photo"
        except Exception:
            pass  # LLM недоступен — ниже сработает эвристика

    if not intent:
        from ..tools.nlu import keyword_intent

        intent = keyword_intent(text, state)

    upd["intent"] = intent
    return upd


def photo_ingest(state: dict) -> dict:
    # Заглушка классификации типа фото (тело/лицо/референс) — уже разложено в state["photos"].
    return {}


# --- Узел gate: точка ветвления №2 (решение в edges.route_from_gate) -----------

def gate(state: dict) -> dict:
    return {}


def appearance_analyzer(state: dict) -> dict:
    photos = state.get("photos", {})
    refs = photos.get("body", []) + photos.get("face", [])
    appr: Appearance = analyze_appearance(refs, hint=_hint(state, "appearance"))
    return {
        "appearance": appr.model_dump(),
        "gate_tries": _bump(state, "appearance"),
        "tool_calls": _log(state, "analyze_appearance", {"n_images": len(refs)}),
    }


def taste_profiler(state: dict) -> dict:
    refs = state.get("photos", {}).get("refs", [])
    sp: StyleProfile = profile_taste(refs, hint=_hint(state, "taste"))
    return {
        "style_profile": sp.model_dump(),
        "gate_tries": _bump(state, "taste"),
        "tool_calls": _log(state, "profile_taste", {"n_refs": len(refs)}),
    }


def preference_dialog(state: dict) -> dict:
    # В боевом Telegram-боте здесь interrupt() и вопрос пользователю.
    # В скелете/бенчмарке добираем недостающее из hints/дефолтов, чтобы граф дошёл до конца.
    c = Constraints(**state.get("constraints", {}))
    d = _hint(state, "constraints")
    merged = c.model_dump()
    merged["occasion"] = merged.get("occasion") or d.get("occasion") or "повседневный"
    merged["budget_rub"] = merged.get("budget_rub") or d.get("budget_rub") or 15000
    if not merged.get("sizes"):
        merged["sizes"] = d.get("sizes") or dict(DEFAULT_SIZES)
    merged["season"] = merged.get("season") or d.get("season") or "деми"
    return {"constraints": merged, "gate_tries": _bump(state, "constraints")}


# --- RAG-поиск по каталогу -----------------------------------------------------

def retriever(state: dict) -> dict:
    c = Constraints(**state.get("constraints", {}))
    sp = StyleProfile(**state.get("style_profile", {}))
    # Один dict и для вызова, и для лога — параметры не разъедутся (eval сверяет лог).
    kwargs = {
        "categories": list(REQUIRED_SLOTS),
        "sizes": c.sizes,
        "budget_rub": c.budget_rub,
        "style_tags": sp.styles + sp.palette,
        "avoid": c.avoid,
    }
    items = search_catalog(**kwargs)
    # «Москва» — не аргумент функции: фильтр moscow_available зашит в поиск; в лог
    # пишем явно, eval tool_calls проверяет именно этот ключ.
    args = {**kwargs, "city": "Москва"}

    # Персонализация (опционально): реранк выдачи контекстным бандитом по фидбэку.
    if settings.personalization and items:
        from ..personalization.bandit import train_from_feedback
        from ..personalization.feedback import load_feedback
        objs = [Item(**i) for i in items]
        fb = load_feedback(user_id=state.get("user_id"))
        if fb:
            bandit = train_from_feedback({o.id: o for o in objs}, fb)
            items = [o.model_dump() for o in bandit.rerank(objs)]

    return {
        "retrieved_items": items,
        "tool_calls": _log(state, "search_catalog", args, ok=bool(items)),
    }


# --- Сборка образа ТОЛЬКО из найденных ID --------------------------------------

def composer(state: dict) -> dict:
    items = [Item(**i) for i in state.get("retrieved_items", [])]
    c = Constraints(**state.get("constraints", {}))
    appr = state.get("appearance", {})
    sp = StyleProfile(**state.get("style_profile", {}))
    budget = c.budget_rub or 10**9
    # Скорер с предвычисленными палитрами (цветотип/вкус постоянны на весь запрос).
    color_of = make_scorer(appr.get("color_type"), sp.palette)
    taste_styles = set(sp.styles)

    def score(it: Item) -> float:
        """Вкус из референсов (стили + палитра) весит больше классических приоров."""
        s = color_of(it.color)
        if taste_styles:
            s += 1.5 * min(2, len(taste_styles & set(it.style_tags)))
        return s

    # Кандидаты по слотам — раскладываем один раз, а не сканируем items на каждый слот.
    pools: dict[str, list[Item]] = {slot: [] for slot in REQUIRED_SLOTS}
    for it in items:
        if it.category in pools:
            pools[it.category].append(it)

    def pick(keyfn):
        remaining = budget
        chosen: list[Item] = []
        for slot in REQUIRED_SLOTS:
            for it in sorted(pools[slot], key=keyfn):
                if it.price <= remaining:
                    chosen.append(it)
                    remaining -= it.price
                    break
        return chosen, remaining

    # Подбор: вкус+гармония — первичный ключ, цена — тай-брейк.
    chosen, remaining = pick(lambda x: (-score(x), x.price))
    # Если из-за цены не покрылись все слоты — откат к «самое дешёвое» (полнота важнее).
    if len({it.category for it in chosen}) < len(REQUIRED_SLOTS):
        chosen, remaining = pick(lambda x: x.price)

    # Reflexion: на повторной сборке учитываем «уроки» прошлого вердикта критика.
    lessons = (state.get("critique") or {}).get("lessons", [])
    lesson_note = f" Учтены уроки: {'; '.join(lessons)}." if lessons else ""
    look = Look(
        items=chosen,
        rationale=(
            f"Собрано под цветотип «{appr.get('color_type', '—')}», повод «{c.occasion}», "
            f"бюджет {budget}₽ (использовано {budget - remaining}₽). "
            f"Цвета подобраны под цветотип и палитру.{lesson_note}"
        ),
    )
    return {"candidate_looks": [look.model_dump()]}


# --- Точка ветвления №3: критик (решение в edges.route_from_critic) ------------

def critic(state: dict) -> dict:
    looks = state.get("candidate_looks", [])
    iteration = state.get("iteration", 0) + 1
    if not looks:
        crit = Critique(verdict="reject", issues=["пустой образ"], judge_score=0.0)
        return {"critique": crit.model_dump(), "iteration": iteration}

    look = Look(**looks[0])
    c = Constraints(**state.get("constraints", {}))
    issues: list[str] = []

    missing = set(REQUIRED_SLOTS) - look.slots
    if missing:
        issues.append(f"не хватает категорий: {', '.join(sorted(missing))}")
    if c.budget_rub is not None and look.total_price > c.budget_rub:
        issues.append(f"превышен бюджет: {look.total_price} > {c.budget_rub}")

    calls = list(state.get("tool_calls", []))
    for it in look.items:
        need = c.sizes.get(it.category)
        if need and need not in it.sizes:
            issues.append(f"нет размера {need} у {it.id}")
        av = check_availability(it.id, need)
        calls.append({"tool": "check_availability", "args": {"item_id": it.id, "size": need}, "ok": True})
        if not av["available"]:
            issues.append(f"нет в наличии: {it.id}")

    # LLM-as-judge: в STUB — максимум (детерминизм), в проде — реальная оценка
    # с презумпцией осознанного приёма (tools/judge.py); при ошибке не блокирует.
    from ..tools.judge import llm_judge

    verdict_j = llm_judge(look, StyleProfile(**state.get("style_profile", {})), c)
    judge_score = verdict_j["score"]
    calls.append({"tool": "llm_judge",
                  "args": {"score": judge_score, "techniques": verdict_j.get("techniques", [])},
                  "ok": True})
    verdict = "approve" if (not issues and judge_score >= 4) else "reject"

    # Reflexion (verbal reinforcement learning): формулируем «урок» для повторной сборки.
    lessons: list[str] = []
    if any("бюджет" in i for i in issues):
        lessons.append("превышен бюджет — на повторе выбирай более дешёвые вещи")
    if any("наличи" in i for i in issues):
        lessons.append("были вещи без наличия — исключай их")
    if any("категор" in i for i in issues):
        lessons.append("образ неполон — добери недостающие категории")

    crit = Critique(verdict=verdict, issues=issues, judge_score=judge_score, lessons=lessons)
    return {"critique": crit.model_dump(), "iteration": iteration, "tool_calls": calls}


def presenter(state: dict) -> dict:
    looks = state.get("candidate_looks", [])
    path = save_look_collage(looks[0], name="look_final") if looks else ""
    lines = ["Готовый образ:"]
    if looks:
        for it in Look(**looks[0]).items:
            lines.append(f"— {it.category}: {it.title} ({it.brand}), {it.price}₽ — {it.store}")
    return {
        "final_looks": looks,
        "answer": "\n".join(lines),
        "tool_calls": _log(state, "save_look_collage", {"path": path}),
    }


# --- Ветка вопрос-совет (RAG) --------------------------------------------------

def advisor_qa(state: dict) -> dict:
    q = state.get("request", "")
    rules = retrieve_styling_rules(q)
    return {
        "answer": "\n".join(rules),
        "tool_calls": _log(state, "retrieve_styling_rules", {"query": q}),
    }
