"""Мини-CLI для демонстрации графа без Telegram.

    PYTHONPATH=src python demo_cli.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from stylist.graph import get_app  # noqa: E402


def main() -> None:
    app = get_app()
    state = {
        "intent": "new_look",
        "request": "Собери образ в офис",
        "appearance": {"color_type": "зима", "body_shape": "песочные часы"},
        "style_profile": {"styles": ["smart-casual"], "palette": ["чёрный", "серый"]},
        "constraints": {"occasion": "офис", "budget_rub": 15000,
                         "sizes": {"верх": "M", "низ": "46", "обувь": "41"}},
    }
    result = app.invoke(state, config={"recursion_limit": 50})
    print(result.get("answer", "нет ответа"))
    print("\nЖурнал tool-вызовов:")
    for c in result.get("tool_calls", []):
        print(f"  · {c['tool']}")


if __name__ == "__main__":
    main()
