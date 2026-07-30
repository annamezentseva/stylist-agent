"""Условные рёбра — три точки принятия решения по контексту.

Именно они превращают линейный pipeline в нелинейный агентный граф.
"""
from __future__ import annotations

from ..config import settings
from ..models import Appearance, Constraints, StyleProfile


# Точка ветвления №1
def route_from_router(state: dict) -> str:
    intent = state.get("intent", "new_look")
    if intent == "question":
        return "advisor_qa"
    if intent == "photo":
        return "photo_ingest"
    return "gate"


# Точка ветвления №2: чего не хватает в профиле?
# Каждый сборщик дёргаем не больше settings.max_gate_tries раз — иначе, если vision
# вернул неполные атрибуты, gate зациклился бы на нём до recursion_limit.
def route_from_gate(state: dict) -> str:
    tries = state.get("gate_tries", {})
    maxt = settings.max_gate_tries
    if not Appearance(**state.get("appearance", {})).is_complete() and tries.get("appearance", 0) < maxt:
        return "appearance_analyzer"
    if not StyleProfile(**state.get("style_profile", {})).is_complete() and tries.get("taste", 0) < maxt:
        return "taste_profiler"
    if not Constraints(**state.get("constraints", {})).is_complete() and tries.get("constraints", 0) < maxt:
        return "preference_dialog"
    return "retriever"


# Точка ветвления №3: петля самокоррекции
def route_from_critic(state: dict) -> str:
    crit = state.get("critique", {})
    if crit.get("verdict") == "reject" and state.get("iteration", 0) < settings.max_iterations:
        return "retriever"
    return "presenter"
