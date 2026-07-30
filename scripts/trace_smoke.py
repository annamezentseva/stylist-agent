"""Трассируемый прогон графа в LangFuse — проверка связки.

    STUB_LLM=true PYTHONPATH=src python scripts/trace_smoke.py

Гоняет офисный кейс в STUB-режиме ($0) с подключённым CallbackHandler и досылает
события. После этого трейс виден в кабинете LangFuse: Tracing -> Traces.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from stylist.config import settings  # noqa: E402
from stylist.graph import get_app, run_config  # noqa: E402
from stylist.obs.langfuse_cb import flush_langfuse, get_langfuse_handler  # noqa: E402
from stylist.tools.catalog import DEFAULT_SIZES  # noqa: E402


def main() -> None:
    handler = get_langfuse_handler()
    if handler is None:
        print("LangFuse handler = None: проверьте LANGFUSE_* в .env и установку langfuse+langchain.")
        return

    # Проверяем, что ключи валидны и host доступен.
    try:
        from langfuse import get_client

        print(f"auth_check: {get_client().auth_check()} | host: {settings.langfuse_host}")
    except Exception as e:
        print(f"auth_check пропущен: {type(e).__name__}: {e}")

    app = get_app()
    state = {
        "intent": "new_look",
        "request": "Собери образ в офис",
        "appearance": {"color_type": "зима", "body_shape": "песочные часы"},
        "style_profile": {"styles": ["smart-casual"], "palette": ["чёрный", "серый"]},
        "constraints": {"occasion": "офис", "budget_rub": 15000,
                        "sizes": dict(DEFAULT_SIZES)},
    }
    result = app.invoke(state, config=run_config(handler, run_name="trace_smoke"))
    print("\nОтвет графа:")
    print(result.get("answer", "нет ответа"))

    flush_langfuse()
    print("\nОтправлено в LangFuse. Открой кабинет -> Tracing -> Traces (run_name=trace_smoke).")


if __name__ == "__main__":
    main()
