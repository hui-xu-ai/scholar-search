"""Policy enforcement: verb/domain allowlists, rate limiting, daily quota.

Every limit here is a floor or ceiling from :mod:`scholar_search.core.config`.
Channels may tighten behaviour, never loosen it.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

from .config import HARD, HardLimits, app_home
from .contracts import VERBS, Action, ChannelManifest, Plan
from .errors import PolicyError

NETWORK_VERBS: frozenset[str] = frozenset({"goto", "click", "select", "type"})
READ_VERBS: frozenset[str] = frozenset(
    {"wait_for", "read_html", "read_text", "scroll", "sleep"}
)


@dataclass(slots=True)
class QuotaState:
    day: str
    used: int = 0


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
        self._last_request: float | None = None
        self._quota = self._load_quota()

    # -- quota ---------------------------------------------------------

    def _today(self) -> str:
        return date.today().isoformat()

    def _load_quota(self) -> QuotaState:
        try:
            raw = json.loads(self._state_path.read_text(encoding="utf-8"))
            state = QuotaState(day=str(raw["day"]), used=int(raw["used"]))
        except (OSError, ValueError, KeyError):
            return QuotaState(day=self._today())

        if state.day != self._today():
            return QuotaState(day=self._today())
        return state

    def _save_quota(self) -> None:
        try:
            self._state_path.parent.mkdir(parents=True, exist_ok=True)
            self._state_path.write_text(
                json.dumps({"day": self._quota.day, "used": self._quota.used}),
                encoding="utf-8",
            )
        except OSError:
            # Quota persistence must never break a search; the in-memory count
            # still applies for this process.
            pass

    @property
    def used_today(self) -> int:
        if self._quota.day != self._today():
            self._quota = QuotaState(day=self._today())
        return self._quota.used

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
                f"plan has {len(actions)} actions, limit is "
                f"{self._limits.max_actions_per_plan}",
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

        if action.verb == "goto":
            url = action.params.get("url")
            if not isinstance(url, str):
                raise PolicyError("goto requires a string url", rule="params.url")
            self.check_url(url, manifest.domains)

        if action.verb == "sleep":
            ms = action.params.get("ms", 0)
            if not isinstance(ms, int) or ms < 0 or ms > 3_000:
                raise PolicyError("sleep must be 0..3000 ms", rule="params.sleep")

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

        if self.remaining_today <= 0:
            raise PolicyError("daily quota exhausted", rule="quota.daily")

        required = self._limits.min_interval_ms + self._jitter()
        now = self._clock()
        slept = 0.0
        if self._last_request is not None:
            elapsed_ms = (now - self._last_request) * 1000
            remaining_ms = required - elapsed_ms
            if remaining_ms > 0:
                slept = remaining_ms / 1000
                self._sleep(slept)
        self._last_request = self._clock()
        return slept

    def note_request(self) -> None:
        if self._quota.day != self._today():
            self._quota = QuotaState(day=self._today())
        self._quota.used += 1
        self._save_quota()
