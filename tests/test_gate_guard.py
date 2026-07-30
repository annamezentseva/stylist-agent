"""Юниты защиты от зацикливания gate (graph/edges.py)."""
from stylist.graph.edges import route_from_gate

_INCOMPLETE_APPEARANCE = {
    # Нет body_shape -> Appearance.is_complete() == False.
    "appearance": {"color_type": "лето"},
    "style_profile": {"styles": ["smart-casual"]},
    "constraints": {"occasion": "офис", "budget_rub": 15000, "sizes": {"верх": "M"}},
}


def test_first_try_goes_to_analyzer():
    state = dict(_INCOMPLETE_APPEARANCE, gate_tries={})
    assert route_from_gate(state) == "appearance_analyzer"


def test_after_limit_moves_on_instead_of_looping():
    # Попытка уже была (лимит по умолчанию 1) -> идём дальше, не по кругу.
    state = dict(_INCOMPLETE_APPEARANCE, gate_tries={"appearance": 1})
    assert route_from_gate(state) == "retriever"


def test_complete_profile_goes_straight_to_retriever():
    state = {
        "appearance": {"color_type": "зима", "body_shape": "песочные часы"},
        "style_profile": {"styles": ["минимализм"]},
        "constraints": {"occasion": "офис", "budget_rub": 15000, "sizes": {"верх": "M"}},
        "gate_tries": {},
    }
    assert route_from_gate(state) == "retriever"
