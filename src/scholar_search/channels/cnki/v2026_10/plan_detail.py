"""Build the CNKI article detail plan."""

from __future__ import annotations

from ....core.contracts import Action, Plan
from .selectors import DETAIL_READY


def build(url: str) -> Plan:
    return Plan(
        channel="cnki",
        purpose="detail",
        actions=(
            Action("goto", {"url": url}),
            Action("wait_for", {"selector": DETAIL_READY, "timeout_ms": 15_000}),
            Action("read_html"),
        ),
    )
