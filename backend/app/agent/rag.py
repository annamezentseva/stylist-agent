"""RAG-ретривер: где агент берёт знания о стиле.

`LocalRetriever` — поиск по markdown-файлам knowledge_base через TF-IDF, без
эмбеддингов и внешних сервисов. Правила лежат абзацами вида:

    **зима, цветотип, палитра.** Зимнему цветотипу идут… (источник: …)

Две детали, которые заметно поднимают качество поиска на такой базе:

  * бонус за совпадение с ТЕГАМИ (жирный префикс). Теги — кураторская разметка,
    поэтому доверяем им больше, чем словам в теле правила: слова «цвет» и
    «палитра» есть во всех правилах о цветотипах и ничего не различают, а тег
    «зима» указывает на тему однозначно;
  * отсечение слабых совпадений по доле от лучшего результата — иначе в выдачу
    к вопросу про зиму попадают правила про лето просто за общие слова.

На отдельном занятии это место меняется на векторный поиск — интерфейс
`Retriever` при этом не трогается.
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
# Жирный префикс в начале блока — список тегов правила.
_TAGS_RE = re.compile(r"^\*\*(.+?)\.?\*\*\s*")

# Во сколько раз совпадение с тегом весомее совпадения в тексте.
_TAG_BOOST = 2.5
# Результаты слабее этой доли от лучшего — отбрасываем как нерелевантные.
_MIN_SCORE_RATIO = 0.5


def _tokenize(text: str) -> list[str]:
    return _WORD_RE.findall(text.lower())


def _strip_markdown(text: str) -> str:
    """Убираем ** и _ — правила показываются пользователю как обычный текст."""
    return text.replace("**", "").replace("_", "")


class LocalRetriever(Retriever):
    """Поиск по markdown-файлам простым TF-IDF с бонусом за теги."""

    def __init__(self, settings: Settings) -> None:
        self._kb_dir = Path(settings.knowledge_base_dir)
        self._rules: list[RetrievedRule] = []
        self._tokenized: list[list[str]] = []
        self._tags: list[set[str]] = []
        self._idf: dict[str, float] = {}
        self._load()

    def _load(self) -> None:
        """Читаем базу знаний в память один раз при инициализации."""
        rules: list[RetrievedRule] = []
        tags: list[set[str]] = []

        for path in sorted(self._kb_dir.glob("*.md")):
            text = path.read_text(encoding="utf-8")
            for block in self._split(text):
                match = _TAGS_RE.match(block)
                # Теги нужны для поиска, но пользователю их показывать незачем —
                # в тексте правила оставляем только само правило.
                tags.append(set(_tokenize(match.group(1))) if match else set())
                body = block[match.end():] if match else block
                rules.append(
                    RetrievedRule(
                        text=_strip_markdown(body).strip(), source=path.name, score=0.0
                    )
                )

        self._rules = rules
        self._tags = tags
        # Индексируем текст вместе с тегами: слово из тегов тоже должно находиться.
        self._tokenized = [
            _tokenize(r.text) + sorted(t) for r, t in zip(rules, tags)
        ]
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

        for rule, tokens, tags in zip(self._rules, self._tokenized, self._tags):
            tf = Counter(tokens)
            score = sum(tf[t] * self._idf.get(t, 0.0) for t in query_terms)
            score += _TAG_BOOST * sum(self._idf.get(t, 0.0) for t in query_terms & tags)
            if score > 0:
                scored.append(rule.model_copy(update={"score": round(score, 3)}))

        if not scored:
            return []

        scored.sort(key=lambda r: r.score, reverse=True)
        cutoff = scored[0].score * _MIN_SCORE_RATIO
        return [r for r in scored[:top_k] if r.score >= cutoff]
