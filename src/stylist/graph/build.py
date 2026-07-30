"""Сборка графа LangGraph: узлы + три условных ребра."""
from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from . import nodes
from .edges import route_from_critic, route_from_gate, route_from_router
from .state import StylistState


def build_graph():
    g = StateGraph(StylistState)

    for name in (
        "router", "photo_ingest", "gate", "appearance_analyzer", "taste_profiler",
        "preference_dialog", "retriever", "composer", "critic", "presenter", "advisor_qa",
    ):
        g.add_node(name, getattr(nodes, name))

    g.add_edge(START, "router")

    # Ветвление №1
    g.add_conditional_edges("router", route_from_router,
                            {"advisor_qa": "advisor_qa", "photo_ingest": "photo_ingest", "gate": "gate"})
    g.add_edge("photo_ingest", "gate")

    # Ветвление №2 (gate добирает недостающие данные и возвращается к себе)
    g.add_conditional_edges("gate", route_from_gate, {
        "appearance_analyzer": "appearance_analyzer",
        "taste_profiler": "taste_profiler",
        "preference_dialog": "preference_dialog",
        "retriever": "retriever",
    })
    g.add_edge("appearance_analyzer", "gate")
    g.add_edge("taste_profiler", "gate")
    g.add_edge("preference_dialog", "gate")

    g.add_edge("retriever", "composer")
    g.add_edge("composer", "critic")

    # Ветвление №3
    g.add_conditional_edges("critic", route_from_critic,
                            {"retriever": "retriever", "presenter": "presenter"})

    g.add_edge("presenter", END)
    g.add_edge("advisor_qa", END)

    return g.compile()


# Готовый к импорту скомпилированный граф.
def get_app():
    return build_graph()
