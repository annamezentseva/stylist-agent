"""Оркестрация: связывает БД, профиль пользователя и агента.

API-слой тонкий — вся логика здесь, как `TicketService` в Workshop 1:
    1) поднять профиль пользователя из БД;
    2) отдать запрос агенту;
    3) сохранить обогащённый профиль и результат в историю.

Сам агент про БД ничего не знает — он получает данные и возвращает решение.
"""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent import Agent, StylistRequest, StylistResult
from app.agent.schemas import Appearance, Constraints, StyleProfile
from app.config import Settings
from app.models import LookRecord, UserProfile
from app.schemas import LookOut, ProfileIn, StylistRequestIn

logger = logging.getLogger(__name__)


class LookNotFound(Exception):
    """Образ не найден — API превратит это в 404."""


class StylistService:
    def __init__(self, session: AsyncSession, agent: Agent, settings: Settings) -> None:
        self._session = session
        self._agent = agent
        self._settings = settings

    # --- Основной сценарий ---

    async def ask(self, data: StylistRequestIn) -> LookOut:
        """Пользователь что-то попросил -> агент отвечает -> сохраняем."""
        logger.info("Stylist request: user=%s text=%s", data.user_id, data.text[:80])

        profile = await self._get_or_create_profile(data.user_id)
        request = StylistRequest(
            user_id=data.user_id,
            text=data.text,
            photos=data.photos or (profile.photos or {}),
            appearance=Appearance(**(profile.appearance or {})),
            style_profile=StyleProfile(**(profile.style_profile or {})),
            constraints=self._merge_constraints(profile, data.constraints),
        )

        result = await self._agent.handle(request)
        logger.info(
            "Agent result: user=%s action=%s items=%s",
            data.user_id, result.action.value, len(result.look.items) if result.look else 0,
        )

        self._persist_profile(profile, result, data)
        record = self._persist_look(data, result)

        await self._session.commit()
        await self._session.refresh(record)
        return self._to_out(record, result)

    # --- Профиль ---

    async def get_profile(self, user_id: str) -> UserProfile:
        return await self._get_or_create_profile(user_id)

    async def save_profile(self, user_id: str, data: ProfileIn) -> UserProfile:
        profile = await self._get_or_create_profile(user_id)
        profile.appearance = data.appearance.model_dump()
        profile.style_profile = data.style_profile.model_dump()
        profile.constraints = data.constraints.model_dump()
        await self._session.commit()
        await self._session.refresh(profile)
        return profile

    async def _get_or_create_profile(self, user_id: str) -> UserProfile:
        profile = await self._session.get(UserProfile, user_id)
        if profile is None:
            profile = UserProfile(
                user_id=user_id, appearance={}, style_profile={}, constraints={}, photos={}
            )
            self._session.add(profile)
            await self._session.flush()
        return profile

    def _merge_constraints(
        self, profile: UserProfile, request_constraints: Constraints
    ) -> Constraints:
        """Постоянные ограничения из профиля + разовые из запроса (запрос главнее)."""
        saved = Constraints(**(profile.constraints or {}))
        data = saved.model_dump()
        for key, value in request_constraints.model_dump().items():
            if value:  # непустое значение из запроса перекрывает сохранённое
                data[key] = value
        return Constraints(**data)

    def _persist_profile(
        self, profile: UserProfile, result: StylistResult, data: StylistRequestIn
    ) -> None:
        """Агент мог доопределить внешность/вкус по фото — сохраняем на будущее."""
        if result.appearance:
            profile.appearance = result.appearance.model_dump()
        if result.style_profile:
            profile.style_profile = result.style_profile.model_dump()
        if data.photos:
            profile.photos = data.photos

    # --- История образов ---

    async def get_look(self, look_id: int) -> LookRecord:
        record = await self._session.get(LookRecord, look_id)
        if record is None:
            raise LookNotFound(look_id)
        return record

    async def list_looks(self, user_id: str, limit: int = 20) -> list[LookRecord]:
        # id как тай-брейк: created_at в SQLite с точностью до секунды, и записи
        # одной секунды иначе возвращались бы в произвольном порядке.
        stmt = (
            select(LookRecord)
            .where(LookRecord.user_id == user_id)
            .order_by(LookRecord.created_at.desc(), LookRecord.id.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    def _persist_look(self, data: StylistRequestIn, result: StylistResult) -> LookRecord:
        record = LookRecord(
            user_id=data.user_id,
            request_text=data.text,
            action=result.action.value,
            answer=result.answer,
            rationale=result.rationale,
            items=[it.model_dump() for it in result.look.items] if result.look else [],
            sources=result.sources,
        )
        self._session.add(record)
        return record

    @staticmethod
    def _to_out(record: LookRecord, result: StylistResult) -> LookOut:
        look = result.look
        return LookOut(
            id=record.id,
            action=result.action.value,
            answer=result.answer,
            items=look.items if look else [],
            rationale=result.rationale,
            sources=result.sources,
            missing=result.missing,
            total_price=look.total_price if look else 0,
        )
