from __future__ import annotations

from pathlib import Path

import pytest

from scholar_search.adapters.fixture import FixtureAdapter
from scholar_search.core.audit import AuditLog
from scholar_search.core.cache import Cache
from scholar_search.core.contracts import SearchQuery
from scholar_search.core.errors import PolicyError
from scholar_search.core.planner import Planner
from scholar_search.core.policy import PolicyEngine
from scholar_search.core.risk import RiskGuard
from scholar_search.core.service import ScholarService
from support import FakeChannel, StubRegistry, make_manifest, make_record


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def time(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += seconds


def build_service(
    tmp_path: Path, channel: FakeChannel, scripts: list[list[dict[str, object]]]
) -> ScholarService:
    clock = FakeClock()
    policy = PolicyEngine(clock=clock.time, sleeper=clock.sleep, state_path=tmp_path / "quota.json")
    risk = RiskGuard(state_path=tmp_path / "cooldown.json")
    audit = AuditLog(path=tmp_path / "audit.jsonl")

    def factory() -> FixtureAdapter:
        return FixtureAdapter(scripts.pop(0))

    return ScholarService(
        registry=StubRegistry(channel),  # type: ignore[arg-type]
        adapter_factory=factory,
        planner_factory=lambda adapter: Planner(adapter, policy, risk, audit),
        policy=policy,
        cache=Cache(path=tmp_path / "cache.sqlite3"),
    )


def test_search_returns_records_and_caches(tmp_path: Path) -> None:
    channel = FakeChannel(manifest=make_manifest(), records=[make_record("Paper A")])
    scripts: list[list[dict[str, object]]] = [
        [
            {"verb": "goto", "data": {}},
            {"verb": "read_html", "data": {"html": "<html>results</html>"}},
        ],
        [
            {"verb": "goto", "data": {}},
            {"verb": "read_html", "data": {"html": "<html>detail</html>"}},
        ],
    ]
    service = build_service(tmp_path, channel, scripts)

    page = service.search(SearchQuery(text="x", channel="fake"))
    assert [record.title for record in page.records] == ["Paper A"]

    # Second call must hit the cache: the detail script is still untouched.
    again = service.search(SearchQuery(text="x", channel="fake"))
    assert again.records[0].title == "Paper A"
    assert len(scripts) == 1


def test_detail_rejects_foreign_host(tmp_path: Path) -> None:
    channel = FakeChannel(manifest=make_manifest())
    service = build_service(tmp_path, channel, [])

    with pytest.raises(PolicyError):
        service.detail("https://evil.test/article/1", channel="fake")


def test_detail_rejects_wrong_path(tmp_path: Path) -> None:
    channel = FakeChannel(manifest=make_manifest())
    service = build_service(tmp_path, channel, [])

    with pytest.raises(PolicyError, match="path"):
        service.detail("https://example.org/other/1", channel="fake")


def test_detail_returns_record(tmp_path: Path) -> None:
    channel = FakeChannel(manifest=make_manifest())
    scripts: list[list[dict[str, object]]] = [
        [
            {"verb": "goto", "data": {}},
            {"verb": "read_html", "data": {"html": "<html>detail</html>"}},
        ]
    ]
    service = build_service(tmp_path, channel, scripts)

    record = service.detail("https://example.org/article/1", channel="fake")
    assert record.title == "A paper"
