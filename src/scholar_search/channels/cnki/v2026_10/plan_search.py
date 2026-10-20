"""Build the CNKI one-box search plan."""

from __future__ import annotations

from urllib.parse import urlencode

from ....core.contracts import Action, Plan, SearchQuery
from .selectors import SEARCH_ENDPOINT, SEARCH_READY

DEFAULT_CROSSIDS = (
    "YSTT4HG0,LSTPFY1C,EMRPGLPA,JUP3MUPD,MPMFIG1A,WQ0UVIAA,"
    "BLZOG7CK,PWFIRAGL,NLBO1Z6R,NN3FJMUV"
)


def build_url(query: SearchQuery) -> str:
    params = {
        "kw": query.text,
        "korder": "SU",
        "crossids": DEFAULT_CROSSIDS,
    }
    return f"{SEARCH_ENDPOINT}?{urlencode(params)}"


def build(query: SearchQuery) -> Plan:
    return Plan(
        channel="cnki",
        purpose="search",
        actions=(
            Action("goto", {"url": build_url(query)}),
            Action("wait_for", {"selector": SEARCH_READY, "timeout_ms": 15_000}),
            Action("read_html"),
        ),
    )
