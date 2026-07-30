from ..config import settings
from .build import build_graph, get_app


def run_config(handler=None, run_name: str | None = None, metadata: dict | None = None) -> dict:
    """Единая точка сборки config для graph.invoke: recursion_limit + observability.

    Все входы (API, бот-скрипты, демо) зовут её вместо ручной сборки dict —
    лимит шагов и правила трейсинга меняются в одном месте.
    """
    cfg: dict = {"recursion_limit": settings.recursion_limit}
    if handler is not None:
        cfg["callbacks"] = [handler]
        if run_name:
            cfg["run_name"] = run_name
        if metadata:
            cfg["metadata"] = metadata
    return cfg


__all__ = ["build_graph", "get_app", "run_config"]
