"""Backend-API вокруг графа (FastAPI).

«Мозг» агента за HTTP. Telegram и веб-UI — тонкие клиенты этого API. Состояние
(профиль, фидбэк, каталог) — в общей БД, поэтому оба клиента видят одно и то же.

Режим «без входа»: единственный пользователь (settings.default_user_id). Публичный
доступ защищается секретом API_TOKEN (заголовок X-API-Token), если он задан.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from ..config import settings
from ..db.repo import CatalogRepo, ProfileRepo
from ..db.session import init_db
from ..graph import get_app, run_config
from ..obs.langfuse_cb import flush_langfuse, get_langfuse_handler
from ..personalization.feedback import record_feedback

GRAPH = None
HANDLER = None  # CallbackHandler LangFuse (None, если ключей нет / пакет не стоит)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    CatalogRepo.seed_if_empty(settings.snapshot_path)
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    global GRAPH, HANDLER
    GRAPH = get_app()
    HANDLER = get_langfuse_handler()
    yield
    flush_langfuse()  # досылаем оставшиеся трейсы при остановке


app = FastAPI(title="Stylist Agent API", version="1.0", lifespan=lifespan)


def require_token(x_api_token: str | None = Header(default=None)) -> None:
    if settings.api_token and x_api_token != settings.api_token:
        raise HTTPException(status_code=401, detail="invalid API token")


class MessageIn(BaseModel):
    text: str
    intent: str | None = None
    user_id: str | None = None


class FeedbackIn(BaseModel):
    item_id: str
    signal: str  # like | dislike | buy | skip
    look_id: str | None = None
    user_id: str | None = None


def _uid(user_id: str | None) -> str:
    return user_id or settings.default_user_id


@app.get("/", include_in_schema=False)
def demo_page() -> FileResponse:
    """Мини веб-UI (демо, Фаза 2 — полноценный SPA): тонкий клиент этого же API."""
    return FileResponse(Path(__file__).parent / "static" / "index.html")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "catalog_items": CatalogRepo.count()}


@app.post("/message", dependencies=[Depends(require_token)])
def message(body: MessageIn) -> dict:
    uid = _uid(body.user_id)
    profile = ProfileRepo.get(uid)
    state = {"user_id": uid, "request": body.text}
    if body.intent:
        state["intent"] = body.intent
    for key in ("appearance", "style_profile", "constraints", "photos"):
        if profile.get(key):
            state[key] = profile[key]

    result = GRAPH.invoke(state, config=run_config(
        HANDLER, run_name="stylist_message",
        metadata={"user_id": uid, "intent": body.intent or ""},
    ))

    # Профиль, наработанный за ход, сохраняем — чтобы продолжить с любого фронта.
    ProfileRepo.save(uid,
                     appearance=result.get("appearance"),
                     style_profile=result.get("style_profile"),
                     constraints=result.get("constraints"))
    return {
        "answer": result.get("answer", ""),
        "final_looks": result.get("final_looks", []),
        "intent": result.get("intent"),
        "retrieved": len(result.get("retrieved_items", [])),
    }


@app.post("/photo", dependencies=[Depends(require_token)])
async def photo(kind: str = Form("refs"), user_id: str | None = Form(None),
                file: UploadFile = File(...)) -> dict:
    uid = _uid(user_id)
    dest = settings.upload_dir / f"{uid}_{kind}_{file.filename}"
    dest.write_bytes(await file.read())
    profile = ProfileRepo.get(uid)
    photos = profile.get("photos", {}) or {}
    photos.setdefault(kind, []).append(str(dest))
    ProfileRepo.save(uid, photos=photos)
    return {"saved": str(dest), "kind": kind, "count": len(photos[kind])}


@app.post("/feedback", dependencies=[Depends(require_token)])
def feedback(body: FeedbackIn) -> dict:
    return record_feedback(_uid(body.user_id), body.item_id, body.signal, body.look_id)


@app.get("/new_arrivals", dependencies=[Depends(require_token)])
def new_arrivals(days: int = 7) -> dict:
    return {"items": CatalogRepo.new_arrivals(since_days=days)}
