"""Фабрика агента: собирает нужную реализацию из настроек."""

import logging

from app.agent.base import LLM, Agent, Catalog, Retriever, Vision
from app.agent.catalog import DbCatalog
from app.agent.llm import OpenAICompatibleLLM
from app.agent.rag import LocalRetriever
from app.agent.simple import SimpleStylistAgent
from app.agent.stub import StubStylistAgent
from app.agent.vision import ApiVision, StubVision
from app.config import Settings, get_settings

logger = logging.getLogger(__name__)


def build_llm(settings: Settings) -> LLM:
    # Провайдер задаётся llm_base_url (OpenAI, OpenRouter, локальная модель).
    return OpenAICompatibleLLM(settings)


def build_retriever(settings: Settings) -> Retriever:
    return LocalRetriever(settings)


def build_catalog(settings: Settings) -> Catalog:
    return DbCatalog()


def build_vision(settings: Settings) -> Vision:
    # Без ключа фото анализировать нечем — возвращаем детерминированную заглушку.
    if settings.stub_vision or not settings.vision_key:
        return StubVision()
    return ApiVision(settings)


def build_agent(settings: Settings | None = None) -> Agent:
    settings = settings or get_settings()

    logger.info(
        "Build agent: agent_type=%s model=%s stub_llm=%s",
        settings.agent_type, settings.llm_model, settings.stub_llm,
    )

    if settings.agent_type == "stub":
        return StubStylistAgent()
    if settings.agent_type == "simple":
        return SimpleStylistAgent(
            build_llm(settings),
            build_retriever(settings),
            build_catalog(settings),
            build_vision(settings),
            settings,
        )

    raise ValueError(f"Unsupported agent_type: {settings.agent_type!r}")
