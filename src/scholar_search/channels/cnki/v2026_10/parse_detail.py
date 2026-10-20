"""Parse a CNKI article detail page."""

from __future__ import annotations

import re

from bs4 import BeautifulSoup, Tag

from ....core.contracts import Record
from ....core.errors import ParseError
from .selectors import DETAIL

_JOURNAL = re.compile(r"《\s*(.+?)\s*》")
_ISSUE = re.compile(r"(\d{4})\s*年\s*(\d+)\s*期")
_VOLUME = re.compile(r"第\s*(\d+)\s*卷")
_PAGES = re.compile(r"(\d+\s*[-–—]\s*\d+)")
_DOI = re.compile(r"10\.\d{4,9}/[^\s，。；;]+")


def _text(node: Tag | None) -> str | None:
    if node is None:
        return None
    value = node.get_text(" ", strip=True)
    return value or None


def _first_text(soup: BeautifulSoup, selector: str) -> str | None:
    for part in selector.split(","):
        node = soup.select_one(part.strip())
        if node is not None:
            value = _text(node)
            if value:
                return value
    return None


def _all_text(soup: BeautifulSoup, selector: str) -> list[str]:
    values: list[str] = []
    for part in selector.split(","):
        for node in soup.select(part.strip()):
            value = _text(node)
            if value:
                values.append(value)
        if values:
            break
    return values


def parse(html: str, url: str) -> Record:
    soup = BeautifulSoup(html, "lxml")

    title = _first_text(soup, DETAIL["title"])
    if not title:
        raise ParseError("detail page has no title")

    top_tip = _first_text(soup, DETAIL["top_tip"]) or ""
    journal_match = _JOURNAL.search(top_tip)
    issue_match = _ISSUE.search(top_tip)
    volume_match = _VOLUME.search(top_tip)
    pages_match = _PAGES.search(top_tip)

    abstract = _first_text(soup, DETAIL["abstract"])
    doi_text = _first_text(soup, DETAIL["doi"]) or ""
    doi_match = _DOI.search(doi_text)

    return Record(
        channel="cnki",
        title=title,
        authors=_all_text(soup, DETAIL["authors"]),
        institution=_first_text(soup, DETAIL["institution"]),
        source=journal_match.group(1) if journal_match else None,
        year=int(issue_match.group(1)) if issue_match else None,
        issue=issue_match.group(2) if issue_match else None,
        volume=volume_match.group(1) if volume_match else None,
        pages=pages_match.group(1).replace(" ", "") if pages_match else None,
        doi=doi_match.group(0) if doi_match else None,
        abstract=abstract,
        keywords=_all_text(soup, DETAIL["keywords"]),
        url=url,
    )
