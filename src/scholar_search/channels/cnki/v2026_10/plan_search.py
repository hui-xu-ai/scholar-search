"""Build the CNKI search plan.

Two entry points exist on the site:

* one-box search (keyword) — the default;
* expert search (field expressions such as ``SU='IPMC' and KY='驱动器'``) —
  reached through ``AdvSearch?type=expert`` and a textarea.

Year filters use the result page's own controls (``#txtStartYear`` /
``#txtEndYear`` / ``#btnFilterYear``); they narrow the current result set
instead of issuing a new query.

Pagination is a client-side page turn (``#PageNext``), so page N costs N-1
extra clicks. The kernel's page-per-call limit keeps that bounded.
"""

from __future__ import annotations

import re
import time

from ....core.contracts import Action, Plan, SearchQuery
from ....core.errors import ChannelError
from .selectors import EXPERT, SEARCH, SEARCH_PAGE, SEARCH_READY

_EXPRESSION = re.compile(
    r"(?:^|[\s(])(?:SU|TKA|KY|TI|FT|AU|FI|AF|FU|AB|LY|DOI|CF)\s*(?:=|%)",
    re.IGNORECASE,
)

PAGE_TURN_MS = 1800
NAV_TIMEOUT_MS = 12_000
WAIT_TIMEOUT_MS = 12_000
INPUT_TIMEOUT_MS = 3_000
CLICK_TIMEOUT_MS = 3_000
READ_TIMEOUT_MS = 10_000
FILTER_WAIT_MS = 8_000


def is_expression(text: str) -> bool:
    return bool(_EXPRESSION.search(text))


def _pagination(query: SearchQuery) -> tuple[Action, ...]:
    actions: list[Action] = []
    for _ in range(max(0, query.page - 1)):
        actions.append(
            Action("click", {"selector": SEARCH["next_page"]}, timeout_ms=CLICK_TIMEOUT_MS)
        )
        actions.append(Action("sleep", {"ms": PAGE_TURN_MS}, timeout_ms=2_000))
        actions.append(
            Action(
                "wait_for",
                {"selector": SEARCH_READY, "timeout_ms": FILTER_WAIT_MS},
                timeout_ms=FILTER_WAIT_MS,
            )
        )
    return tuple(actions)


def _page_size(query: SearchQuery) -> tuple[Action, ...]:
    """Ask the result grid for 50 rows when the caller wants more than 20."""

    if query.limit <= 20:
        return ()
    return (
        Action(
            "click", {"selector": SEARCH["page_size_open"]}, timeout_ms=CLICK_TIMEOUT_MS
        ),
        Action("sleep", {"ms": 400}, timeout_ms=2_000),
        Action(
            "click", {"selector": SEARCH["page_size_50"]}, timeout_ms=CLICK_TIMEOUT_MS
        ),
        Action("sleep", {"ms": 1200}, timeout_ms=2_000),
    )


def build(query: SearchQuery) -> Plan:
    if query.source_types:
        raise ChannelError("source-type filters are not implemented for the cnki channel yet")
    if query.sort != "relevance":
        raise ChannelError("custom sort is not implemented for the cnki channel yet")

    # A unique parameter forces a real navigation, so the result grid always
    # starts from its default state (20 rows, page 1).
    nonce = int(time.time() * 1000)

    if is_expression(query.text):
        expert_url = f"{EXPERT['page']}&t={nonce}"
        head = (
            Action("goto", {"url": expert_url}, timeout_ms=NAV_TIMEOUT_MS),
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
        )
    else:
        search_url = f"{SEARCH_PAGE}?t={nonce}"
        head = (
            Action("goto", {"url": search_url}, timeout_ms=NAV_TIMEOUT_MS),
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
        )

    actions = (
        *head,
        Action(
            "wait_for",
            {"selector": SEARCH_READY, "timeout_ms": WAIT_TIMEOUT_MS},
            timeout_ms=WAIT_TIMEOUT_MS,
        ),
        *_page_size(query),
        *_pagination(query),
        Action("read_html", timeout_ms=READ_TIMEOUT_MS),
    )
    return Plan(channel="cnki", purpose="search", actions=actions)
