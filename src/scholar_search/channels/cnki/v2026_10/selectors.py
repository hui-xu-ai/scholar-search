"""CSS selectors for the CNKI 2026.10 layout.

Verified against live pages on 2026-10-20. Change them only with a fixture.
"""

from __future__ import annotations

SEARCH = {
    "input": "input.search-input",
    "submit": "input.search-btn",
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
    "next_page": "#PageNext",
}

EXPERT = {
    "page": "https://kns.cnki.net/kns8s/AdvSearch?type=expert",
    "input": "textarea.majorSearch",
    "submit": "input.btn-search",
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

SEARCH_PAGE = "https://kns.cnki.net/kns8s/search"
SEARCH_READY = ".result-table-list tbody tr"
DETAIL_READY = "#ChDivSummary, h1"
