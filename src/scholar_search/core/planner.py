"""Plan validation and execution.

Sequencing lives here, not in adapters: this is the only place that can stop a
plan between two actions when a risk signal appears.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from .audit import AuditLog
from .contracts import ActionOutcome, BrowserAdapter, ChannelManifest, Plan
from .policy import NETWORK_VERBS, PolicyEngine
from .risk import RiskGuard


@dataclass(slots=True)
class Planner:
    adapter: BrowserAdapter
    policy: PolicyEngine
    risk: RiskGuard
    audit: AuditLog

    def run(self, plan: Plan, manifest: ChannelManifest) -> tuple[ActionOutcome, ...]:
        self.risk.ensure_ready()
        self.policy.validate_plan(plan, manifest)

        outcomes: list[ActionOutcome] = []
        for action in plan.actions:
            network = action.verb in NETWORK_VERBS
            if network:
                self.policy.wait_turn()

            started = time.perf_counter()
            outcome = self.adapter.execute(action, timeout_ms=action.timeout_ms)
            elapsed_ms = outcome.duration_ms or int((time.perf_counter() - started) * 1000)

            if network:
                self.policy.note_request()

            self.audit.action(
                channel=plan.channel,
                purpose=plan.purpose,
                verb=action.verb,
                ok=outcome.ok,
                duration_ms=elapsed_ms,
            )
            outcomes.append(outcome)

            signal = self.risk.inspect(outcome)
            if signal is not None:
                blocked = self.risk.trip(signal, f"{signal.value} after {action.verb}")
                self.audit.risk(
                    channel=plan.channel,
                    signal=signal.value,
                    cooldown_until=blocked.cooldown_until,
                )
                raise blocked

        return tuple(outcomes)
