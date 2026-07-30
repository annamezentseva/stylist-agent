"""Vision: анализ фотографий (внешность и вкус) со структурным выводом.

Две реализации одного интерфейса `Vision`:
  * StubVision  — детерминированные атрибуты без сети и ключей (по умолчанию).
                  Позволяет всему приложению работать «из коробки».
  * ApiVision   — боевой режим: мультимодальная модель извлекает атрибуты из
                  фото и сразу валидируется в Appearance / StyleProfile.

ВАЖНО (приватность): в боевом режиме фото уходят к внешнему провайдеру. Не
логируйте сами изображения.
"""

from __future__ import annotations

import base64
import json
import mimetypes
from pathlib import Path

import httpx

from app.agent.base import Vision
from app.agent.schemas import Appearance, StyleProfile
from app.config import Settings


# --- Заглушка: работает без ключей, даёт стабильный результат для демо/тестов ---


class StubVision(Vision):
    async def analyze_appearance(
        self, image_refs: list[str], hint: dict | None = None
    ) -> Appearance:
        h = hint or {}
        return Appearance(
            color_type=h.get("color_type", "зима"),
            undertone=h.get("undertone", "холодный"),
            contrast=h.get("contrast", "высокий"),
            body_shape=h.get("body_shape", "песочные часы"),
            face_shape=h.get("face_shape", "овал"),
        )

    async def profile_taste(
        self, image_refs: list[str], hint: dict | None = None
    ) -> StyleProfile:
        h = hint or {}
        return StyleProfile(
            styles=h.get("styles", ["smart-casual", "минимализм"]),
            palette=h.get("palette", ["чёрный", "серый", "белый"]),
            silhouettes=h.get("silhouettes", ["прямой"]),
            likes=h.get("likes", ["лаконичность"]),
            dislikes=h.get("dislikes", ["принты"]),
        )


# --- Боевой режим: мультимодальный вызов API со structured output ---


_APPEARANCE_PROMPT = (
    "Ты стилист-колорист. По фото фигуры и/или лица определи внешность и верни "
    "поля: color_type (весна/лето/осень/зима), undertone (тёплый/холодный/"
    "нейтральный), contrast (низкий/средний/высокий), body_shape (тип фигуры), "
    "face_shape (форма лица). Если признак не определить — оставь null."
)

_TASTE_PROMPT = (
    "Ты стилист. Это фото-референсы образов, которые нравятся человеку. Обобщи "
    "вкус и верни: styles (стилевые направления), palette (частые цвета), "
    "silhouettes (силуэты), likes (что человек любит), dislikes (чего избегает). "
    "Списки — из коротких слов на русском."
)


def _image_url(ref: str) -> str:
    """http(s)-ссылка как есть; локальный путь/base64 -> data-URL."""
    if ref.startswith(("http://", "https://")):
        return ref
    p = Path(ref)
    if p.exists():
        media = mimetypes.guess_type(str(p))[0] or "image/jpeg"
        data = base64.standard_b64encode(p.read_bytes()).decode("utf-8")
        return f"data:{media};base64,{data}"
    return f"data:image/jpeg;base64,{ref}"


class ApiVision(Vision):
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._headers = {
            "Authorization": f"Bearer {settings.vision_key}",
            "Content-Type": "application/json",
        }

    async def _extract(self, image_refs: list[str], prompt: str, schema):
        """Один структурный vision-вызов: инструкция + картинки -> модель."""
        json_schema = json.dumps(schema.model_json_schema(), ensure_ascii=False)
        content: list[dict] = [
            {
                "type": "text",
                "text": (
                    f"{prompt}\n\nВерни СТРОГО один JSON-объект по схеме "
                    f"(без markdown):\n{json_schema}"
                ),
            }
        ]
        for r in image_refs:
            content.append({"type": "image_url", "image_url": {"url": _image_url(r)}})

        payload = {
            "model": self._settings.vision_model,
            "temperature": self._settings.llm_temperature,
            "messages": [{"role": "user", "content": content}],
            "response_format": {"type": "json_object"},
        }
        url = f"{self._settings.llm_base_url}/chat/completions"
        async with httpx.AsyncClient(timeout=self._settings.llm_timeout_seconds) as client:
            resp = await client.post(url, headers=self._headers, json=payload)
            resp.raise_for_status()
            raw = resp.json()["choices"][0]["message"]["content"]
        return schema.model_validate_json(raw)

    async def analyze_appearance(
        self, image_refs: list[str], hint: dict | None = None
    ) -> Appearance:
        if not image_refs:
            return Appearance()  # нет фото — пустой профиль, без краша
        return await self._extract(image_refs, _APPEARANCE_PROMPT, Appearance)

    async def profile_taste(
        self, image_refs: list[str], hint: dict | None = None
    ) -> StyleProfile:
        if not image_refs:
            return StyleProfile()
        return await self._extract(image_refs, _TASTE_PROMPT, StyleProfile)
