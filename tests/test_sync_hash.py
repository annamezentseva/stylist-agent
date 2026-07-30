"""Юниты контент-хеша дельта-синхронизации (db/repo.py, используется rag/sync.py)."""
from stylist.db.repo import content_hash as _content_hash

_REC = {"price": 1490, "in_stock": True, "moscow_available": True,
        "title": "Чёрная футболка", "sizes": ["S", "M"]}


def test_hash_is_deterministic():
    assert _content_hash(dict(_REC)) == _content_hash(dict(_REC))


def test_price_change_changes_hash():
    changed = dict(_REC, price=1990)
    assert _content_hash(changed) != _content_hash(_REC)


def test_size_order_does_not_matter():
    reordered = dict(_REC, sizes=["M", "S"])
    assert _content_hash(reordered) == _content_hash(_REC)
