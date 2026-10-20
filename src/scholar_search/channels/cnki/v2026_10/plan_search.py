"""Build the CNKI search plan.

Two entry points exist on the site:

* one-box search (keyword) — the default;
* expert search (field expressions such as ``SU='IPMC' and KY='驱动器'``) —
  reached through ``AdvSearch?type=expert`` and a textarea.

Pagination is a client-side page turn (``#PageNext``), so page N costs N-1
extra clicks. The kernel's page-per-call limit keeps that bounded.
"""

from __future__ import annotations

import re

from ....core.contracts import Action, Plan, SearchQuery
from ....core.errors import ChannelError
from .selectors import EXPERT, SEARCH, SEARCH_PAGE, SEARCH_READY

_EXPRESSION = re.compile(
    r"(?:^|[\s(])(?:SU|TKA|KY|TI|FT|AU|FI|AF|FU|AB|LY|DOI|CF)\s*(?:=|%)",
    re.IGNORECASE,
)

PAGE_TURN_MS = 1800
NAV_TIMEOUT_MS = 15_000
WAIT_TIMEOUT_MS = 15_000
INPUT_TIMEOUT_MS = 5_000
CLICK_TIMEOUT_MS = 5_000
READ_TIMEOUT_MS = 15_000


def is_expression(text: str) -> bool:
    return bool(_EXPRESSION.search(text))


def _pagination(query: SearchQuery) -> tuple[Action, ...]:
    actions: list[Action] = []
    for _ in range(max(0, query.page - 1)):
        actions.append(
            Action("click", {"selector": SEARCH["next_page"]}, timeout_ms=CLICK_TIMEOUT_MS)
        )
        actions.append(Action("sleep", {"ms": PAGE_TURN_MS}, timeout_ms=5_000))
        actions.append(
            Action(
                "wait_for",
                {"selector": SEARCH_READY, "timeout_ms": 10_000},
                timeout_ms=10_000,
            )
        )
    return tuple(actions)


def build(query: SearchQuery) -> Plan:
    if query.year_from is not None or query.year_to is not None:
        raise ChannelError("year filters are not implemented for the cnki channel yet")
    if query.source_types:
        raise ChannelError("source-type filters are not implemented for the cnki channel yet")
    if query.sort != "relevance":
        raise ChannelError("custom sort is not implemented for the cnki channel yet")

    if is_expression(query.text):
        actions = (
            Action("goto", {"url": EXPERT["page"]}, timeout_ms=NAV_TIMEOUT_MS),
            Action(
                "wait_for",
                {"selector": EXPERT["input"], "timeout_ms": WAIT_TIMEOUT_MS},
                timeout_ms=WAIT_TIMEOUT_MS,
            ),
            Action(
                "type",
                {"selector": EXPERT["input"], "text": query.text},
                timeout_ms=INPUT_TIMEOUT_MS,
            ),
            Action(
                "click",
                {"selector": EXPERT["submit"]},
                timeout_ms=CLICK_TIMEOUT_MS,
            ),
            Action(
                "wait_for",
                {"selector": SEARCH_READY, "timeout_ms": WAIT_TIMEOUT_MS},
                timeout_ms=WAIT_TIMEOUT_MS,
            ),
            *_pagination(query),
            Action("read_html", timeout_ms=READ_TIMEOUT_MS),
        )
    else:
        actions = (
            Action("goto", {"url": SEARCH_PAGE}, timeout_ms=NAV_TIMEOUT_MS),
            Action(
                "wait_for",
                {"selector": SEARCH["input"], "timeout_ms": WAIT_TIMEOUT_MS},
                timeout_ms=WAIT_TIMEOUT_MS,
            ),
            Action(
                "type",
                {"selector": SEARCH["input"], "text": query.text},
                timeout_ms=INPUT_TIMEOUT_MS,
            ),
            Action(
                "click",
                {"selector": SEARCH["submit"]},
                timeout_ms=CLICK_TIMEOUT_MS,
            ),
            Action(
                "wait_for",
                {"selector": SEARCH_READY, "timeout_ms": WAIT_TIMEOUT_MS},
                timeout_ms=WAIT_TIMEOUT_MS,
            ),
            *_pagination(query),
            Action("read_html", timeout_ms=READ_TIMEOUT_MS),
        )
    return Plan(channel="cnki", purpose="search", actions=actions)
