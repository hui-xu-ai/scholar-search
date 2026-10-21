"""Build the CNKI article detail plan."""

from __future__ import annotations

from ....core.contracts import Action, Plan
from .selectors import DETAIL_READY

# The inner wait must stay below the 15s action budget: otherwise the outer TCP
# deadline fires first and the final page/risk snapshot never reaches the kernel.
DETAIL_WAIT_MS = 8_000


def build(url: str) -> Plan:
    return Plan(
        channel="cnki",
        purpose="detail",
        actions=(
            Action("goto", {"url": url}),
            Action("wait_for", {"selector": DETAIL_READY, "timeout_ms": DETAIL_WAIT_MS}),
            Action("read_html"),
        ),
    )
