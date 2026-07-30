"""Vision-инструмент — облачный API (OpenAI GPT-vision) со структурным выводом.

В STUB-режиме возвращает детерминированные атрибуты, чтобы граф и бенчмарк
работали без ключей и оплаты. В боевом режиме (STUB_LLM=false) мультимодальная
модель OpenAI извлекает атрибуты из фото и сразу валидируется в Appearance /
StyleProfile через structured outputs (response_format=<pydantic-модель>).

ВАЖНО (security): фото уходят к внешнему провайдеру. В LangFuse-трейсы сами
изображения не попадают — поле photos маскируется на границе observability
(см. obs/langfuse_cb).
"""
from __future__ import annotations

import base64
import mimetypes
from pathlib import Path

from ..config import settings
from ..models import Appearance, StyleProfile
from .llm import get_client


def _image_url(ref: str) -> str:
    """URL для image_url: http(s)-ссылка как есть, локальный путь/base64 -> data-URL."""
    if ref.startswith(("http://", "https://")):
        return ref
    p = Path(ref)
    if p.exists():
        media = mimetypes.guess_type(str(p))[0] or "image/jpeg"
        data = base64.standard_b64encode(p.read_bytes()).decode("utf-8")
        return f"data:{media};base64,{data}"
    return f"data:image/jpeg;base64,{ref}"


def _extract(image_refs: list[str], prompt: str, output_model):
    """Один структурный vision-вызов: инструкция + картинки -> валидированная модель."""
    content: list[dict] = [{"type": "text", "text": prompt}]
    for r in image_refs:
        content.append({"type": "image_url", "image_url": {"url": _image_url(r)}})

    comp = get_client().chat.completions.parse(
        model=settings.vision_model,
        messages=[{"role": "user", "content": content}],
        response_format=output_model,
    )
    return comp.choices[0].message.parsed or output_model()


_APPEARANCE_PROMPT = (
    "Ты стилист-колорист. По фото фигуры и/или лица определи внешность человека и "
    "верни поля: color_type (весна/лето/осень/зима), undertone (тёплый/холодный/нейтральный), "
    "contrast (низкий/средний/высокий), body_shape (тип фигуры, напр. «песочные часы», «груша», "
    "«прямоугольник»), face_shape (форма лица). Если признак не определить — оставь его null."
)

_TASTE_PROMPT = (
    "Ты стилист. Это фото-референсы образов, которые нравятся человеку. Обобщи вкус и верни: "
    "styles (стилевые направления, напр. «smart-casual», «минимализм»), palette (частые цвета), "
    "silhouettes (силуэты), likes (что человек явно любит), dislikes (чего избегает). "
    "Списки — из коротких слов/словосочетаний на русском."
)


def analyze_appearance(image_refs: list[str], hint: dict | None = None) -> Appearance:
    """Фото тела/лица -> цветотип, тип фигуры, контраст."""
    if settings.stub_llm:
        h = hint or {}
        return Appearance(
            color_type=h.get("color_type", "зима"),
            undertone=h.get("undertone", "холодный"),
            contrast=h.get("contrast", "высокий"),
            body_shape=h.get("body_shape", "песочные часы"),
            face_shape=h.get("face_shape", "овал"),
        )
    if not image_refs:
        return Appearance()  # нет фото — пустой профиль (gate-guard пойдёт дальше, без краша)
    return _extract(image_refs, _APPEARANCE_PROMPT, Appearance)


def profile_taste(image_refs: list[str], hint: dict | None = None) -> StyleProfile:
    """Фото-референсы нравящихся образов -> вектор вкуса (обязательный этап)."""
    if settings.stub_llm:
        h = hint or {}
        return StyleProfile(
            styles=h.get("styles", ["smart-casual", "минимализм"]),
            palette=h.get("palette", ["чёрный", "серый", "белый"]),
            silhouettes=h.get("silhouettes", ["прямой"]),
            likes=h.get("likes", ["лаконичность"]),
            dislikes=h.get("dislikes", ["принты"]),
        )
    if not image_refs:
        return StyleProfile()  # нет референсов — пустой вкус (gate-guard пойдёт дальше)
    return _extract(image_refs, _TASTE_PROMPT, StyleProfile)
