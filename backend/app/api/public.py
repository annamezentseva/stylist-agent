"""Публичный API: то, чем пользуется клиент на странице стилиста."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_stylist_service
from app.schemas import LookOut, LookSummary, ProfileIn, ProfileOut, StylistRequestIn
from app.services.stylist import LookNotFound, StylistService

router = APIRouter(prefix="/api", tags=["public"])


@router.post("/ask", response_model=LookOut, status_code=status.HTTP_201_CREATED)
async def ask(
    data: StylistRequestIn, service: StylistService = Depends(get_stylist_service)
) -> LookOut:
    """Задать вопрос или попросить образ. Агент обработает сразу."""
    return await service.ask(data)


@router.get("/looks", response_model=list[LookSummary])
async def list_looks(
    user_id: str = "demo", service: StylistService = Depends(get_stylist_service)
) -> list[LookSummary]:
    """История образов и ответов пользователя."""
    records = await service.list_looks(user_id)
    return [LookSummary.model_validate(r) for r in records]


@router.get("/looks/{look_id}")
async def get_look(
    look_id: int, service: StylistService = Depends(get_stylist_service)
) -> dict:
    try:
        record = await service.get_look(look_id)
    except LookNotFound:
        raise HTTPException(status_code=404, detail="Образ не найден") from None
    return {
        "id": record.id,
        "action": record.action,
        "answer": record.answer,
        "rationale": record.rationale,
        "items": record.items,
        "sources": record.sources,
    }


@router.get("/profile", response_model=ProfileOut)
async def get_profile(
    user_id: str = "demo", service: StylistService = Depends(get_stylist_service)
) -> ProfileOut:
    profile = await service.get_profile(user_id)
    return ProfileOut.model_validate(profile)


@router.put("/profile", response_model=ProfileOut)
async def save_profile(
    data: ProfileIn,
    user_id: str = "demo",
    service: StylistService = Depends(get_stylist_service),
) -> ProfileOut:
    """Сохранить анкету пользователя (внешность, вкус, постоянные ограничения)."""
    profile = await service.save_profile(user_id, data)
    return ProfileOut.model_validate(profile)
