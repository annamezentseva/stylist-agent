# Бэкенд агента-стилиста

Архитектура повторяет Workshop 1: тонкий API-слой, сервис-оркестратор и слой
агента за абстрактными интерфейсами.

## Быстрый старт

```bash
cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
```

```bash
cd backend && .venv/bin/uvicorn app.main:app --reload
```

Ключи не нужны: по умолчанию `STUB_LLM=true`, агент работает на эвристиках.
Документация API — http://localhost:8000/docs

## Структура

```
app/
├── main.py           точка входа: БД, каталог, агент-синглтон, роутеры
├── config.py         все настройки из .env (get_settings)
├── database.py       движок SQLAlchemy, сессии (по умолчанию SQLite-файл)
├── models.py         3 таблицы: items, user_profiles, looks
├── schemas.py        контракт с фронтендом (HTTP-схемы)
├── seed.py           заливка каталога из data/catalog.json при старте
├── api/
│   ├── deps.py       Dependency Injection: сессия + агент -> сервис
│   └── public.py     эндпоинты /api/ask, /api/looks, /api/profile
├── services/
│   └── stylist.py    оркестрация: профиль -> агент -> сохранение
└── agent/            «мозг», ничего не знает про HTTP и БД
    ├── base.py       интерфейсы: LLM, Retriever, Catalog, Vision, Agent
    ├── schemas.py    доменный контракт: StylistRequest -> StylistResult
    ├── factory.py    сборка реализации по настройкам
    ├── simple.py     рабочий агент: NLU -> профиль -> RAG / подбор
    ├── stub.py       заглушка (AGENT_TYPE=stub)
    ├── llm.py        клиент OpenRouter (+ структурный вывод по схеме)
    ├── rag.py        TF-IDF поиск по knowledge_base/*.md
    ├── vision.py     анализ фото: заглушка и боевой режим
    ├── catalog.py    поиск вещей в БД
    ├── compose.py    сборка образа по слотам (чистая функция)
    └── prompts/      промпты отдельным слоем
```

## Как работает запрос

```
POST /api/ask
   │
   ├─ StylistService: поднимает профиль пользователя из БД
   │
   ├─ SimpleStylistAgent.handle()
   │     1. понять запрос      интент + бюджет/повод/ограничения
   │     2. обогатить профиль  внешность и вкус из фото (vision)
   │     3a. вопрос   -> RAG по knowledge_base -> совет      (action=advice)
   │     3b. образ    -> каталог + композиция по слотам      (action=look)
   │         не вышло -> чего не хватает                     (action=need_info)
   │
   └─ StylistService: сохраняет профиль и запись в историю
```

## Данные

* `data/catalog.json` — каталог вещей. Заливается в БД при первом старте.
  Чтобы обновить: отредактируйте JSON и удалите `stylist.db`.
* `knowledge_base/*.md` — правила стиля обычными абзацами. Каждый абзац —
  отдельный фрагмент для поиска. Дописывать можно прямо в файлы.

## Включить настоящую LLM

В `.env` поставьте `STUB_LLM=false` и укажите `OPENROUTER_API_KEY`. Тогда разбор
запроса и советы пойдут через модель. Для анализа фото — `STUB_VISION=false`.

## Проверка

```bash
curl -s -X POST localhost:8000/api/ask -H 'Content-Type: application/json' -d '{"text":"собери образ на свидание до 12000"}'
```
