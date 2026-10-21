"""Replay adapter for offline tests.

A fixture is an ordered script. Each step answers exactly one action; the verb
must match, so a channel that changes its plan fails loudly instead of silently
reading the wrong page.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from ...core.contracts import Action, ActionOutcome


@dataclass(frozen=True, slots=True)
class FixtureStep:
    verb: str
    ok: bool = True
    data: Mapping[str, Any] = field(default_factory=dict)
    error: str | None = None
    duration_ms: int = 1


class FixtureAdapter:
    """Executes a pre-recorded script of action outcomes."""

    name = "fixture"

    def __init__(self, steps: Sequence[FixtureStep | Mapping[str, Any]]) -> None:
        self._steps: list[FixtureStep] = [
            step if isinstance(step, FixtureStep) else FixtureStep(**step) for step in steps
        ]
        self._cursor = 0
        self.closed = False

    @property
    def remaining(self) -> int:
        return len(self._steps) - self._cursor

    def execute(self, action: Action, *, timeout_ms: int) -> ActionOutcome:
        if self.closed:
            raise RuntimeError("adapter is closed")
        if self._cursor >= len(self._steps):
            raise AssertionError(
                f"fixture exhausted at {action.verb!r}; expected no further actions"
            )

        step = self._steps[self._cursor]
        if step.verb != action.verb:
            raise AssertionError(
                f"fixture expected {step.verb!r}, channel requested {action.verb!r}"
            )
        self._cursor += 1

        url = action.params.get("url") if action.verb == "goto" else None
        return ActionOutcome(
            action=action,
            ok=step.ok,
            data=dict(step.data),
            error=step.error,
            duration_ms=step.duration_ms,
            url=url if isinstance(url, str) else None,
        )

    def close(self) -> None:
        self.closed = True
