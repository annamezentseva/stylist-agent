"""Telegram-бот-стилист (aiogram v3) — тонкий HTTP-клиент backend-API.

Бот НЕ крутит граф у себя: он шлёт сообщения/фото в API (stylist.api.app) и
показывает ответ. Тот же API обслуживает и веб-UI.

Поток: пользователь выбирает тип кадра (фигура/лицо/референсы) → шлёт фото →
жмёт «Собрать образ» → бот дергает /message, показывает образ и кнопки 👍/👎/🛒,
нажатия которых уходят в /feedback (сигналы для контекстного бандита).

Запуск (нужен поднятый API по API_URL и TELEGRAM_TOKEN в .env):
    PYTHONPATH=src python -m stylist.bot.telegram_app
"""
from __future__ import annotations

import asyncio
import io

import httpx

from ..config import settings

_HEADERS = {"X-API-Token": settings.api_token} if settings.api_token else {}

# Один клиент на процесс бота: keep-alive переиспользует соединение к API,
# вместо холодного TCP/TLS-рукопожатия на каждый запрос.
_client = httpx.AsyncClient(base_url=settings.api_url, headers=_HEADERS, timeout=120)

# Лёгкое состояние в памяти процесса (для одного инстанса бота этого достаточно):
_KIND: dict[int, str] = {}          # chat_id -> тип следующего фото (body/face/refs)
_LAST_LOOK: dict[int, list[str]] = {}  # chat_id -> id вещей последнего образа

_KIND_LABEL = {"body": "фигуры", "face": "лица", "refs": "референсов"}


# --- HTTP-обёртки над API (async, легко тестируются отдельно от Telegram) -----

async def _post(path: str, **kwargs) -> dict:
    """Единый POST к backend-API: общий клиент, raise_for_status, json."""
    r = await _client.post(path, **kwargs)
    r.raise_for_status()
    return r.json()


async def api_message(text: str, uid: str, intent: str | None = None) -> dict:
    payload = {"text": text, "user_id": uid}
    if intent:
        payload["intent"] = intent
    return await _post("/message", json=payload)


async def api_photo(data: bytes, kind: str, uid: str, filename: str = "photo.jpg") -> dict:
    return await _post("/photo", data={"kind": kind, "user_id": uid},
                       files={"file": (filename, data, "image/jpeg")})


async def api_feedback(item_id: str, signal: str, uid: str, look_id: str | None = None) -> dict:
    payload = {"item_id": item_id, "signal": signal, "user_id": uid}
    if look_id:
        payload["look_id"] = look_id
    return await _post("/feedback", json=payload)


# --- Разметка кнопок ----------------------------------------------------------

def _main_kb():
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📸 Фото фигуры", callback_data="kind:body"),
         InlineKeyboardButton(text="🙂 Фото лица", callback_data="kind:face")],
        [InlineKeyboardButton(text="👗 Референсы образов", callback_data="kind:refs")],
        [InlineKeyboardButton(text="✨ Собрать образ", callback_data="build")],
    ])


def _feedback_kb():
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="👍 Нравится", callback_data="fb:like"),
        InlineKeyboardButton(text="👎 Не то", callback_data="fb:dislike"),
        InlineKeyboardButton(text="🛒 Куплю", callback_data="fb:buy"),
    ]])


def _remember_look(chat_id: int, data: dict) -> None:
    looks = data.get("final_looks") or []
    ids = [it["id"] for lk in looks for it in lk.get("items", [])]
    if ids:
        _LAST_LOOK[chat_id] = ids


# --- Хендлеры -----------------------------------------------------------------

def _register(dp) -> None:
    from aiogram import F
    from aiogram.filters import Command, CommandStart
    from aiogram.types import CallbackQuery, Message

    @dp.message(CommandStart())
    async def start(m: Message) -> None:
        await m.answer(
            "Привет! Я бот-стилист.\n\n"
            "1) Выберите тип кадра кнопкой и пришлите фото (фигуры / лица / "
            "3–7 референсов нравящихся образов).\n"
            "2) Напишите повод и бюджет словами (например «образ в офис, до 15000»).\n"
            "3) Нажмите «Собрать образ» — подберу вещи, доступные в Москве.\n\n"
            "⚠️ Фото обрабатываются облачным vision-сервисом (только атрибуты, не сами снимки).",
            reply_markup=_main_kb(),
        )

    @dp.message(Command("help"))
    async def help_(m: Message) -> None:
        await m.answer("Кнопкой выберите тип фото → пришлите фото → «Собрать образ». "
                       "Текстом можно задать повод/бюджет или задать вопрос по стилю.",
                       reply_markup=_main_kb())

    @dp.callback_query(F.data.startswith("kind:"))
    async def set_kind(cq: CallbackQuery) -> None:
        kind = cq.data.split(":", 1)[1]
        _KIND[cq.message.chat.id] = kind
        await cq.answer(f"Жду фото {_KIND_LABEL.get(kind, kind)}")
        await cq.message.answer(f"Ок, следующее фото сохраню как «{_KIND_LABEL.get(kind, kind)}». Пришлите его.")

    @dp.callback_query(F.data == "build")
    async def build(cq: CallbackQuery) -> None:
        uid = str(cq.from_user.id)
        await cq.answer("Собираю образ…")
        try:
            data = await api_message("Собери образ", uid, intent="new_look")
        except Exception as e:  # noqa: BLE001
            await cq.message.answer(f"Сервис недоступен: {e}")
            return
        _remember_look(cq.message.chat.id, data)
        answer = data.get("answer") or "Не удалось собрать образ."
        await cq.message.answer(answer, reply_markup=_feedback_kb() if _LAST_LOOK.get(cq.message.chat.id) else None)

    @dp.callback_query(F.data.startswith("fb:"))
    async def feedback(cq: CallbackQuery) -> None:
        signal = cq.data.split(":", 1)[1]
        uid = str(cq.from_user.id)
        ids = _LAST_LOOK.get(cq.message.chat.id, [])
        if not ids:
            await cq.answer("Сначала соберите образ")
            return
        try:
            # Реакция ставится всем вещам образа — шлём параллельно, не последовательно.
            await asyncio.gather(*(api_feedback(item_id, signal, uid) for item_id in ids))
        except Exception as e:  # noqa: BLE001
            await cq.answer("Не удалось записать")
            await cq.message.answer(f"Ошибка фидбэка: {e}")
            return
        label = {"like": "👍 учту", "dislike": "👎 учту", "buy": "🛒 отметил покупку"}.get(signal, "ок")
        await cq.answer(label)

    @dp.message(F.photo)
    async def on_photo(m: Message) -> None:
        uid = str(m.from_user.id)
        kind = _KIND.get(m.chat.id, "refs")
        buf = io.BytesIO()
        await m.bot.download(m.photo[-1], destination=buf)
        try:
            res = await api_photo(buf.getvalue(), kind, uid, filename=f"{m.photo[-1].file_id}.jpg")
        except Exception as e:  # noqa: BLE001
            await m.answer(f"Не удалось загрузить фото: {e}")
            return
        await m.answer(
            f"Фото {_KIND_LABEL.get(kind, kind)} сохранено (всего {res.get('count', '?')}). "
            "Пришлите ещё или нажмите «Собрать образ».",
            reply_markup=_main_kb(),
        )

    @dp.message(F.text)
    async def on_text(m: Message) -> None:
        uid = str(m.from_user.id)
        try:
            data = await api_message(m.text or "", uid)  # интент определит router графа
        except Exception as e:  # noqa: BLE001
            await m.answer(f"Сервис недоступен: {e}")
            return
        _remember_look(m.chat.id, data)
        kb = _feedback_kb() if _LAST_LOOK.get(m.chat.id) and (data.get("final_looks")) else _main_kb()
        await m.answer(data.get("answer") or "…", reply_markup=kb)


def main() -> None:
    if not settings.telegram_token:
        raise SystemExit("Заполните TELEGRAM_TOKEN в .env")
    from aiogram import Bot, Dispatcher

    bot = Bot(settings.telegram_token)
    dp = Dispatcher()
    _register(dp)
    dp.run_polling(bot)


if __name__ == "__main__":
    main()
