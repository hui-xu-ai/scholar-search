"""Build the CNKI search plan.

The one-box URL alone does not run a search in the 2026.10 UI; the page must be
driven through its input and submit button.
"""

from __future__ import annotations

from ....core.contracts import Action, Plan, SearchQuery
from .selectors import SEARCH, SEARCH_PAGE, SEARCH_READY


def build(query: SearchQuery) -> Plan:
    return Plan(
        channel="cnki",
        purpose="search",
        actions=(
            Action("goto", {"url": SEARCH_PAGE}),
            Action("wait_for", {"selector": SEARCH["input"], "timeout_ms": 15_000}),
            Action("type", {"selector": SEARCH["input"], "text": query.text}),
            Action("click", {"selector": SEARCH["submit"]}),
            Action("wait_for", {"selector": SEARCH_READY, "timeout_ms": 20_000}),
            Action("read_html"),
        ),
    )
