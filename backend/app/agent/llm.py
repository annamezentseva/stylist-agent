"""Клиент LLM через OpenRouter (OpenAI-совместимый Chat Completions API).

Слой, который прячет конкретного провайдера. Агент вызывает `complete` и
`complete_structured`, ничего не зная про OpenRouter, ключи и HTTP. Один-в-один
идея из Workshop 1: структурный вызов кладёт в system JSON Schema модели,
включает response_format=json_object и валидирует ответ через pydantic.
"""

from __future__ import annotations

import json

import httpx

from app.agent.base import LLM, TModel
from app.config import Settings


class OpenRouterLLM(LLM):
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._headers = {
            "Authorization": f"Bearer {settings.openrouter_api_key}",
            "Content-Type": "application/json",
        }

    def _messages(self, system: str, user: str) -> list[dict]:
        return [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]

    async def _chat(self, payload: dict) -> dict:
        """Единая точка похода в API."""
        url = f"{self._settings.openrouter_base_url}/chat/completions"
        async with httpx.AsyncClient(timeout=self._settings.llm_timeout_seconds) as client:
            response = await client.post(url, headers=self._headers, json=payload)
            response.raise_for_status()
            return response.json()

    async def complete(self, system: str, user: str) -> str:
        """Свободный текстовый ответ."""
        payload = {
            "model": self._settings.llm_model,
            "temperature": self._settings.llm_temperature,
            "messages": self._messages(system, user),
        }
        data = await self._chat(payload)
        return data["choices"][0]["message"]["content"].strip()

    async def complete_structured(
        self, system: str, user: str, schema: type[TModel]
    ) -> TModel:
        """Ответ, распарсенный и провалидированный в pydantic-схему `schema`.

        1) добавляем в system JSON Schema модели (schema.model_json_schema());
        2) включаем response_format={"type": "json_object"};
        3) валидируем: schema.model_validate_json(raw). Мусор -> ValidationError.
        """
        json_schema = json.dumps(schema.model_json_schema(), ensure_ascii=False, indent=2)
        system_with_schema = (
            f"{system}\n\n"
            "Ответь СТРОГО одним JSON-объектом по следующей JSON Schema, "
            "без markdown и пояснений:\n"
            f"{json_schema}"
        )
        payload = {
            "model": self._settings.llm_model,
            "temperature": self._settings.llm_temperature,
            "messages": self._messages(system_with_schema, user),
            "response_format": {"type": "json_object"},
        }
        data = await self._chat(payload)
        raw = data["choices"][0]["message"]["content"]
        return schema.model_validate_json(raw)
