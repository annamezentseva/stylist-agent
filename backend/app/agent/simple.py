"""Основная реализация агента-стилиста: RAG + каталог + композиция.

Прямолинейный пайплайн, без саморефлексии — аналог `SimpleRagAgent` из
Workshop 1, но для стиля:

    1. Понять запрос            — интент + ограничения (LLM или эвристика).
    2. Обогатить профиль        — внешность и вкус из фото (vision или заглушка).
    3a. Ветка «вопрос»          — совет по базе знаний (RAG [+ LLM]).
    3b. Ветка «образ»           — поиск по каталогу + жадная композиция.

Работает «из коробки» без ключей: при STUB_LLM/STUB_VISION используются
эвристики и детерминированный vision. С ключами те же шаги идут через LLM.
"""

from __future__ import annotations

import logging

from app.agent.base import LLM, Agent, Catalog, Retriever, Vision
from app.agent.compose import compose_look, occasion_tags
from app.agent.prompts import (
    SYSTEM_PROMPT_ADVICE,
    SYSTEM_PROMPT_NLU,
    RequestNLU,
    build_context,
    build_user_prompt,
    heuristic_nlu,
)
from app.agent.schemas import (
    Appearance,
    Constraints,
    StyleProfile,
    StylistAction,
    StylistRequest,
    StylistResult,
)
from app.config import Settings

logger = logging.getLogger(__name__)


class SimpleStylistAgent(Agent):
    def __init__(
        self,
        llm: LLM,
        retriever: Retriever,
        catalog: Catalog,
        vision: Vision,
        settings: Settings,
    ) -> None:
        self._llm = llm
        self._retriever = retriever
        self._catalog = catalog
        self._vision = vision
        self._settings = settings

    async def handle(self, request: StylistRequest) -> StylistResult:
        constraints, intent = await self._understand(request)
        appearance = await self._appearance(request)
        style = await self._taste(request)

        logger.info(
            "Stylist handle: user=%s intent=%s occasion=%s budget=%s",
            request.user_id, intent, constraints.occasion, constraints.budget_rub,
        )

        if intent == "question":
            return await self._advice(request.text, appearance, style, constraints)
        return await self._build_look(appearance, style, constraints)

    # --- Шаг 1: понять запрос ---------------------------------------------

    async def _understand(self, request: StylistRequest) -> tuple[Constraints, str]:
        """Интент + ограничения. LLM при наличии ключей, иначе эвристика."""
        if self._settings.stub_llm:
            parsed = heuristic_nlu(request.text)
        else:
            try:
                parsed = await self._llm.complete_structured(
                    SYSTEM_PROMPT_NLU, request.text, RequestNLU
                )
            except Exception as exc:  # недоступность API/битый JSON -> фолбэк
                logger.warning("NLU LLM failed, fallback to heuristic: %s", exc)
                parsed = heuristic_nlu(request.text)

        base = request.constraints
        constraints = Constraints(
            occasion=base.occasion or parsed.occasion,
            budget_rub=base.budget_rub or parsed.budget_rub,
            season=base.season or parsed.season,
            sizes=base.sizes,
            avoid=base.avoid or parsed.avoid,
        )
        intent = request.intent or parsed.intent
        return constraints, intent

    # --- Шаг 2: обогатить профиль из фото ---------------------------------

    async def _appearance(self, request: StylistRequest) -> Appearance:
        if request.appearance.is_known():
            return request.appearance
        refs = request.photos.get("body", []) + request.photos.get("face", [])
        return await self._vision.analyze_appearance(refs)

    async def _taste(self, request: StylistRequest) -> StyleProfile:
        if request.style_profile.is_known():
            return request.style_profile
        return await self._vision.profile_taste(request.photos.get("refs", []))

    # --- Шаг 3a: совет по стилю (вопрос) ----------------------------------

    async def _advice(
        self,
        text: str,
        appearance: Appearance,
        style: StyleProfile,
        constraints: Constraints,
    ) -> StylistResult:
        rules = await self._retriever.search(text, self._settings.rag_top_k)
        if not rules:
            return StylistResult(
                action=StylistAction.NEED_INFO,
                rationale="В базе знаний нет правил под этот вопрос.",
                missing=["уточните вопрос про цвет, фигуру, повод или сочетание"],
                appearance=appearance, style_profile=style, constraints=constraints,
            )

        sources = [r.source for r in rules]
        if self._settings.stub_llm:
            answer = "\n\n".join(r.text for r in rules)  # без LLM — отдаём правила
        else:
            try:
                answer = await self._llm.complete(
                    SYSTEM_PROMPT_ADVICE, build_user_prompt(text, build_context(rules))
                )
            except Exception as exc:
                logger.warning("Advice LLM failed, fallback to rules: %s", exc)
                answer = "\n\n".join(r.text for r in rules)

        return StylistResult(
            action=StylistAction.ADVICE,
            answer=answer,
            sources=sources,
            rationale="Ответ по базе знаний стиля.",
            appearance=appearance, style_profile=style, constraints=constraints,
        )

    # --- Шаг 3b: собрать образ --------------------------------------------

    async def _build_look(
        self,
        appearance: Appearance,
        style: StyleProfile,
        constraints: Constraints,
    ) -> StylistResult:
        taste_tags = list(set(style.styles) | set(occasion_tags(constraints.occasion)))
        items = await self._catalog.search(
            sizes=constraints.sizes,
            budget_rub=constraints.budget_rub,
            style_tags=taste_tags,
            avoid=constraints.avoid,
        )
        look = compose_look(
            items, constraints, appearance, style, self._settings.default_budget_rub
        )

        if not look.items:
            return StylistResult(
                action=StylistAction.NEED_INFO,
                rationale="Под заданные ограничения ничего не нашлось.",
                missing=["смягчите бюджет или снимите часть ограничений"],
                appearance=appearance, style_profile=style, constraints=constraints,
            )

        return StylistResult(
            action=StylistAction.LOOK,
            look=look,
            rationale=look.rationale,
            appearance=appearance, style_profile=style, constraints=constraints,
        )
