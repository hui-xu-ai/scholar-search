"""CSS selectors for the CNKI 2026.10 layout.

Every selector here is a guess that must be verified against a recorded page.
Change them only together with a new fixture.
"""

from __future__ import annotations

SEARCH = {
    "row": ".result-table-list tbody tr",
    "title_link": "td.name a.fz14",
    "authors": "td.author a.KnowledgeNetLink",
    "source": "td.source a",
    "date": "td.date",
    "citations": "td.quote",
    "downloads": "td.download",
    "checkbox": "input.cbItem",
    "total": ".pagerTitleCell",
    "page_marker": ".countPageMark",
}

DETAIL = {
    "title": "h1",
    "authors": ".author a, #authorpart a",
    "institution": ".orgn, #organization",
    "abstract": "#ChDivSummary",
    "keywords": ".keywords a, #keywords a",
    "doi": ".doi",
    "top_tip": ".top-tip",
}

SEARCH_ENDPOINT = "https://kns.cnki.net/kns8s/defaultresult/index"
DETAIL_READY = "#ChDivSummary, h1"
SEARCH_READY = ".result-table-list tbody tr"
