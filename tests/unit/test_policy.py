from __future__ import annotations

from typing import cast

import pytest

from scholar_search.core.config import HARD
from scholar_search.core.contracts import Action, Plan, Verb
from scholar_search.core.errors import PolicyError
from scholar_search.core.policy import PolicyEngine
from support import make_manifest


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0
        self.sleeps: list[float] = []

    def time(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


def engine(clock: FakeClock | None = None, **kwargs: object) -> PolicyEngine:
    clock = clock or FakeClock()
    return PolicyEngine(clock=clock.time, sleeper=clock.sleep, **kwargs)  # type: ignore[arg-type]


def test_rejects_unknown_verb() -> None:
    policy = engine()
    action = Action(cast(Verb, "eval"), {"code": "1+1"})
    plan = Plan(channel="fake", purpose="search", actions=(action,))
    with pytest.raises(PolicyError, match="unknown verb"):
        policy.validate_plan(plan, make_manifest())


def test_rejects_verb_not_in_manifest() -> None:
    policy = engine()
    plan = Plan(channel="fake", purpose="search", actions=(Action("click", {"selector": "a"}),))
    with pytest.raises(PolicyError, match="does not allow"):
        policy.validate_plan(plan, make_manifest(verbs=("goto", "read_html")))


def test_rejects_non_https() -> None:
    policy = engine()
    with pytest.raises(PolicyError, match="https"):
        policy.check_url("http://example.org/", ("example.org",))


def test_rejects_foreign_domain() -> None:
    policy = engine()
    with pytest.raises(PolicyError, match="not allowed"):
        policy.check_url("https://evil.test/", ("example.org",))


def test_allows_subdomain() -> None:
    policy = engine()
    policy.check_url("https://kns.example.org/x", ("example.org",))


def test_rejects_oversized_plan() -> None:
    policy = engine()
    actions = tuple(Action("read_html") for _ in range(HARD.max_actions_per_plan + 1))
    plan = Plan(channel="fake", purpose="search", actions=actions)
    with pytest.raises(PolicyError, match="actions"):
        policy.validate_plan(plan, make_manifest())


def test_sleep_is_bounded() -> None:
    policy = engine()
    plan = Plan(channel="fake", purpose="search", actions=(Action("sleep", {"ms": 5000}),))
    with pytest.raises(PolicyError, match="sleep"):
        policy.validate_plan(plan, make_manifest())


def test_wait_turn_enforces_interval() -> None:
    clock = FakeClock()
    policy = engine(clock)
    first = policy.wait_turn()
    assert first == 0.0
    second = policy.wait_turn()
    assert second >= HARD.min_interval_ms / 1000
    assert clock.sleeps


def test_quota_exhaustion() -> None:
    clock = FakeClock()
    policy = engine(clock)
    for _ in range(HARD.daily_request_limit):
        policy.wait_turn()
        policy.note_request()
    assert policy.remaining_today == 0
    with pytest.raises(PolicyError, match="quota"):
        policy.wait_turn()
