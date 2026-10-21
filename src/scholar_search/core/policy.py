"""Policy enforcement: verb/domain allowlists, rate limiting, daily quota.

Every limit here is a floor or ceiling from :mod:`scholar_search.core.config`.
Channels may tighten behaviour, never loosen it.

The quota file is the single source of truth. It is read and written under an
inter-process lock so two servers sharing one data directory cannot each spend
the same last request or skip the interval.
"""

from __future__ import annotations

import json
import os
import threading
import time
from collections.abc import Callable, Iterable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import IO
from urllib.parse import urlparse

from .config import HARD, HardLimits, app_home
from .contracts import VERBS, Action, ChannelManifest, Plan
from .errors import PolicyError
from .params import validate_params

NETWORK_VERBS: frozenset[str] = frozenset({"goto", "click", "select", "type"})
READ_VERBS: frozenset[str] = frozenset({"wait_for", "read_html", "read_text", "scroll", "sleep"})


@dataclass(slots=True)
class QuotaState:
    day: str
    used: int = 0
    last: float | None = None


_MEMORY_LOCK = threading.Lock()


@contextmanager
def _exclusive(path: Path) -> Iterator[IO[bytes]]:
    """Cross-process lock on a sidecar file (Windows and POSIX)."""

    path.parent.mkdir(parents=True, exist_ok=True)
    handle = path.open("a+b")
    try:
        if os.name == "nt":
            import msvcrt

            handle.seek(0)
            if handle.tell() == 0:
                handle.write(b"0")
                handle.flush()
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)  # type: ignore[attr-defined]
        yield handle
    finally:
        try:
            if os.name == "nt":
                import msvcrt

                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)  # type: ignore[attr-defined]
        finally:
            handle.close()


class PolicyEngine:
    """Validates plans and meters their execution."""

    def __init__(
        self,
        limits: HardLimits = HARD,
        *,
        clock: Callable[[], float] = time.monotonic,
        sleeper: Callable[[float], None] = time.sleep,
        jitter: Callable[[], float] | None = None,
        state_path: Path | None = None,
    ) -> None:
        self._limits = limits
        self._clock = clock
        self._sleep = sleeper
        self._jitter = jitter or (lambda: 0.0)
        self._state_path = state_path or (app_home() / "state" / "quota.json")
        self._lock_path = self._state_path.with_suffix(".lock")
        self._fallback = QuotaState(day=self._today())

    # -- quota ---------------------------------------------------------

    def _today(self) -> str:
        return date.today().isoformat()

    def _read(self) -> QuotaState:
        try:
            raw = json.loads(self._state_path.read_text(encoding="utf-8"))
            state = QuotaState(
                day=str(raw["day"]),
                used=int(raw["used"]),
                last=float(raw["last"]) if raw.get("last") is not None else None,
            )
        except (OSError, ValueError, KeyError, TypeError):
            return self._fallback
        if state.day != self._today():
            return QuotaState(day=self._today())
        return state

    @contextmanager
    def _guard(self) -> Iterator[None]:
        """Cross-process lock when available; process lock otherwise."""

        try:
            with _exclusive(self._lock_path):
                yield
        except OSError:
            with _MEMORY_LOCK:
                yield

    def _write(self, state: QuotaState) -> None:
        try:
            self._state_path.parent.mkdir(parents=True, exist_ok=True)
            self._state_path.write_text(
                json.dumps({"day": state.day, "used": state.used, "last": state.last}),
                encoding="utf-8",
            )
            self._fallback = state
        except OSError:
            # Persistence may fail; the in-process counter still applies.
            self._fallback = state

    @property
    def used_today(self) -> int:
        return self._read().used

    @property
    def remaining_today(self) -> int:
        return max(0, self._limits.daily_request_limit - self.used_today)

    # -- validation ----------------------------------------------------

    def validate_plan(self, plan: Plan, manifest: ChannelManifest) -> None:
        actions = plan.actions
        if not actions:
            raise PolicyError("plan is empty", rule="plan.empty")
        if len(actions) > self._limits.max_actions_per_plan:
            raise PolicyError(
                f"plan has {len(actions)} actions, limit is {self._limits.max_actions_per_plan}",
                rule="plan.size",
            )

        total_ms = sum(action.timeout_ms for action in actions)
        if total_ms > self._limits.max_plan_seconds * 1000:
            raise PolicyError(
                f"plan budget {total_ms}ms exceeds {self._limits.max_plan_seconds}s",
                rule="plan.duration",
            )

        for action in actions:
            self._validate_action(action, manifest)

    def _validate_action(self, action: Action, manifest: ChannelManifest) -> None:
        if action.verb not in VERBS:
            raise PolicyError(f"unknown verb {action.verb!r}", rule="verb.unknown")
        if action.verb not in manifest.verbs:
            raise PolicyError(
                f"channel {manifest.channel!r} does not allow {action.verb!r}",
                rule="verb.not_allowed",
            )
        if action.timeout_ms < 0 or action.timeout_ms > 15_000:
            raise PolicyError(
                f"timeout {action.timeout_ms}ms is outside 0..15000",
                rule="action.timeout",
            )

        error = validate_params(action.verb, action.params)
        if error is not None:
            raise PolicyError(f"invalid parameters for {action.verb}: {error}", rule=error)

        if action.verb == "goto":
            self.check_url(str(action.params["url"]), manifest.domains)

    def check_url(self, url: str, domains: Iterable[str]) -> None:
        parsed = urlparse(url)
        if parsed.scheme != "https":
            raise PolicyError("only https URLs are allowed", rule="url.scheme")
        host = (parsed.hostname or "").casefold()
        allowed = {d.casefold() for d in domains}
        if not any(host == d or host.endswith("." + d) for d in allowed):
            raise PolicyError(f"host {host!r} is not allowed", rule="url.domain")

    # -- metering ------------------------------------------------------

    def wait_turn(self) -> float:
        """Sleep until the next request is allowed. Returns the slept seconds."""

        required = self._limits.min_interval_ms + self._jitter()
        slept = 0.0
        with self._guard():
            state = self._read()
            if state.used >= self._limits.daily_request_limit:
                raise PolicyError("daily quota exhausted", rule="quota.daily")

            now = self._clock()
            if state.last is not None:
                remaining_ms = required - (now - state.last) * 1000
                if remaining_ms > 0:
                    slept = remaining_ms / 1000
                    self._sleep(slept)
                    now = self._clock()
            state.last = now
            self._write(state)
        return slept

    def note_request(self) -> None:
        with self._guard():
            state = self._read()
            state.used += 1
            state.last = self._clock()
            self._write(state)
