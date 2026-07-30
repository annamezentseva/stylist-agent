"""Юниты цветовой гармонии (tools/color.py) — чистая функция, без API и БД."""
from stylist.tools.color import color_score


def test_season_palette_match_beats_mismatch():
    # Белый — в палитре «лета»; горчичный — тёплый конфликт для холодного типа.
    assert color_score("белый", "лето", []) > color_score("горчичный", "лето", [])


def test_warm_color_penalized_for_cool_season():
    assert color_score("терракотовый", "зима", []) < 0


def test_cool_color_penalized_for_warm_season():
    assert color_score("лавандовый", "осень", []) < 0


def test_taste_palette_bonus():
    base = color_score("синий", "зима", [])
    with_taste = color_score("синий", "зима", ["синий"])
    assert with_taste > base


def test_neutral_gets_small_bonus_without_season():
    assert color_score("чёрный", None, None) > 0


def test_compound_color_tokens():
    # «серо-голубой» должен матчиться и целиком, и по части «голубой».
    assert color_score("серо-голубой", "лето", []) > 0


def test_taste_palette_outweighs_season_palette():
    # Принцип «правила — пол, не потолок»: цвет из ВКУСА пользователя (не в палитре
    # цветотипа) должен обыгрывать цвет из палитры цветотипа (не во вкусе).
    taste_color = color_score("лавандовый", "зима", ["лавандовый"])  # вкус, вне сезона
    season_color = color_score("изумруд", "зима", ["лавандовый"])    # сезон, вне вкуса
    assert taste_color > season_color
