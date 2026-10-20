from __future__ import annotations

from pathlib import Path

from scholar_search.core.cache import Cache


class FakeClock:
    def __init__(self) -> None:
        self.now = 100.0

    def time(self) -> float:
        return self.now


def test_set_and_get(tmp_path: Path) -> None:
    cache = Cache(path=tmp_path / "c.sqlite3")
    cache.set("k", {"a": 1})
    assert cache.get("k") == {"a": 1}


def test_missing_key_returns_none(tmp_path: Path) -> None:
    assert Cache(path=tmp_path / "c.sqlite3").get("nope") is None


def test_expired_entry_is_dropped(tmp_path: Path) -> None:
    clock = FakeClock()
    cache = Cache(path=tmp_path / "c.sqlite3", ttl_seconds=10, clock=clock.time)
    cache.set("k", "v")
    clock.now += 11
    assert cache.get("k") is None


def test_overwrite_keeps_latest(tmp_path: Path) -> None:
    cache = Cache(path=tmp_path / "c.sqlite3")
    cache.set("k", 1)
    cache.set("k", 2)
    assert cache.get("k") == 2
