"""RAG-ретривер: где агент берёт знания о стиле.

`LocalRetriever` — простой поиск по markdown-файлам knowledge_base через TF-IDF,
без эмбеддингов и внешних сервисов. Правила колористики, фигур, дресс-кода и
трендовых приёмов лежат обычными абзацами; ретривер находит самые релевантные
под запрос пользователя. На отдельном занятии это место меняется на векторный
поиск — интерфейс `Retriever` при этом не трогается.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from pathlib import Path

from app.agent.base import Retriever
from app.agent.schemas import RetrievedRule
from app.config import Settings

_WORD_RE = re.compile(r"\w+", re.UNICODE)


def _tokenize(text: str) -> list[str]:
    return _WORD_RE.findall(text.lower())


class LocalRetriever(Retriever):
    """Поиск по markdown-файлам простым TF-IDF (без эмбеддингов)."""

    def __init__(self, settings: Settings) -> None:
        self._kb_dir = Path(settings.knowledge_base_dir)
        self._rules: list[RetrievedRule] = []
        self._tokenized: list[list[str]] = []
        self._idf: dict[str, float] = {}
        self._load()

    def _load(self) -> None:
        """Читаем базу знаний в память один раз при инициализации."""
        rules: list[RetrievedRule] = []
        for path in sorted(self._kb_dir.glob("*.md")):
            text = path.read_text(encoding="utf-8")
            for block in self._split(text):
                rules.append(RetrievedRule(text=block, source=path.name, score=0.0))

        self._rules = rules
        self._tokenized = [_tokenize(r.text) for r in rules]
        self._idf = self._compute_idf(self._tokenized)

    @staticmethod
    def _split(text: str) -> list[str]:
        """Режем документ на смысловые блоки по пустым строкам."""
        blocks = [b.strip() for b in re.split(r"\n\s*\n", text)]
        return [b for b in blocks if len(b) > 30]

    @staticmethod
    def _compute_idf(docs: list[list[str]]) -> dict[str, float]:
        n = len(docs) or 1
        df: Counter[str] = Counter()
        for tokens in docs:
            for term in set(tokens):
                df[term] += 1
        return {term: math.log((n + 1) / (freq + 1)) + 1.0 for term, freq in df.items()}

    async def search(self, query: str, top_k: int = 3) -> list[RetrievedRule]:
        query_terms = set(_tokenize(query))
        scored: list[RetrievedRule] = []
        for rule, tokens in zip(self._rules, self._tokenized):
            tf = Counter(tokens)
            score = sum(tf[t] * self._idf.get(t, 0.0) for t in query_terms)
            if score > 0:
                scored.append(rule.model_copy(update={"score": round(score, 3)}))

        scored.sort(key=lambda r: r.score, reverse=True)
        return scored[:top_k]
