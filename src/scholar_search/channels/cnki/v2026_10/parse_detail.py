"""Parse a CNKI article detail page (2026.10 layout).

The header is a list of ``li.top-space`` rows (DOI, 专辑, 专题, 分类号,
网络出版时间, …), authors live in ``h3.author``, and the abstract is
``#ChDivSummary``. Volume/issue/pages only exist for print issues; online-first
articles have a publication date instead.
"""

from __future__ import annotations

import re

from bs4 import BeautifulSoup, Tag

from ....core.contracts import Record
from ....core.errors import ParseError
from .selectors import DETAIL

_SUFFIX = re.compile(r"\s*(?:附视频|[（(](?:视频|网络首发|优先出版)[）)])\s*$")
_YEAR = re.compile(r"(19|20)\d{2}")
_AFFILIATION_MARK = re.compile(r"[\d,，\s]+$")
_TIME_KEYS = ("在线公开时间", "网络出版时间", "出版时间", "发表时间")

# Print issues put the citation line in ``.top-first``:
#   力学学报 . 2022 ,54 (01) : 184-195 查看该刊数据库收录来源
_TOP_LINE = re.compile(
    r"\.\s*(?P<year>(?:19|20)\d{2})\s*,\s*(?P<volume>\d+)\s*"
    r"(?:\((?P<issue>[^)]*)\))?\s*:\s*(?P<pages>[0-9\-–,]+)"
)


def _text(node: Tag | None) -> str | None:
    if node is None:
        return None
    value = node.get_text(" ", strip=True)
    return value or None


def _clean_title(value: str) -> str:
    return _SUFFIX.sub("", value).strip()


def _rows(soup: BeautifulSoup) -> dict[str, str]:
    rows: dict[str, str] = {}
    for item in soup.select("li.top-space"):
        label = item.select_one(".rowtit")
        value = item.select_one("p")
        if label is None or value is None:
            continue
        key = re.sub(r"[：:\s]", "", label.get_text())
        text = value.get_text(" ", strip=True)
        if key and text:
            rows[key] = text
    return rows


def _pick(rows: dict[str, str], *needles: str) -> str | None:
    for key, value in rows.items():
        if all(needle in key for needle in needles):
            return value
    return None


def _authors(soup: BeautifulSoup) -> tuple[list[str], str | None]:
    blocks = soup.select("h3.author")
    if not blocks:
        return [], None

    authors: list[str] = []
    for link in blocks[0].select("a"):
        name = _AFFILIATION_MARK.sub("", link.get_text(strip=True))
        if name and "@" not in name:
            authors.append(name)
    institution = _text(blocks[1]) if len(blocks) > 1 else None
    return authors, institution


def _source(soup: BeautifulSoup) -> tuple[str | None, str]:
    node = soup.select_one(".top-first")
    if node is None:
        return None, ""
    value = node.get_text(" ", strip=True)
    source = value.split(" . ")[0].strip() or None
    return source, value


def parse(html: str, url: str) -> Record:
    soup = BeautifulSoup(html, "lxml")

    title_node = soup.select_one(DETAIL["title"]) or soup.select_one("h1")
    raw_title = _text(title_node)
    if not raw_title:
        raise ParseError("detail page has no title")
    title = _clean_title(raw_title)

    authors, institution = _authors(soup)
    rows = _rows(soup)

    doi = _pick(rows, "DOI")
    published = next((rows[key] for key in _TIME_KEYS if key in rows), None)
    year = None
    if published:
        match = _YEAR.search(published)
        year = int(match.group()) if match else None

    source, top_line = _source(soup)
    volume = issue = pages = None
    match = _TOP_LINE.search(top_line)
    if match:
        year = year or int(match.group("year"))
        volume = match.group("volume")
        issue = match.group("issue")
        pages = match.group("pages")

    keywords = [
        link.get_text(strip=True).strip(";；,，、")
        for link in soup.select("p.keywords a")
        if link.get_text(strip=True)
    ]

    return Record(
        channel="cnki",
        title=title,
        authors=authors,
        institution=institution,
        source=source,
        year=year,
        volume=volume or _pick(rows, "卷"),
        issue=issue or _pick(rows, "期"),
        pages=pages or _pick(rows, "页"),
        doi=doi,
        abstract=_text(soup.select_one(DETAIL["abstract"])),
        keywords=keywords,
        url=url,
    )
