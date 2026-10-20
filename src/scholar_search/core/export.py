"""RIS and EndNote text rendering.

Only bibliographic text is produced. Nothing is written to disk and no
download endpoint is ever contacted.
"""

from __future__ import annotations

from collections.abc import Iterable

from .contracts import Record


def _clean(value: str | None) -> str:
    return " ".join(value.split()) if value else ""


def to_ris(records: Iterable[Record]) -> str:
    lines: list[str] = []
    for record in records:
        lines.append("TY  - JOUR")
        lines.append(f"TI  - {_clean(record.title)}")
        for author in record.authors:
            lines.append(f"AU  - {_clean(author)}")
        if record.source:
            lines.append(f"T2  - {_clean(record.source)}")
        if record.year:
            lines.append(f"PY  - {record.year}")
        if record.volume:
            lines.append(f"VL  - {_clean(record.volume)}")
        if record.issue:
            lines.append(f"IS  - {_clean(record.issue)}")
        if record.pages:
            first, _, last = record.pages.partition("-")
            lines.append(f"SP  - {_clean(first)}")
            if last:
                lines.append(f"EP  - {_clean(last)}")
        if record.doi:
            lines.append(f"DO  - {_clean(record.doi)}")
        if record.abstract:
            lines.append(f"AB  - {_clean(record.abstract)}")
        for keyword in record.keywords:
            lines.append(f"KW  - {_clean(keyword)}")
        if record.url:
            lines.append(f"UR  - {_clean(record.url)}")
        lines.append("ER  - ")
        lines.append("")
    return "\n".join(lines)


def to_endnote(records: Iterable[Record]) -> str:
    lines: list[str] = []
    for record in records:
        lines.append("%0 Journal Article")
        lines.append(f"%T {_clean(record.title)}")
        for author in record.authors:
            lines.append(f"%A {_clean(author)}")
        if record.source:
            lines.append(f"%J {_clean(record.source)}")
        if record.year:
            lines.append(f"%D {record.year}")
        if record.volume:
            lines.append(f"%V {_clean(record.volume)}")
        if record.issue:
            lines.append(f"%N {_clean(record.issue)}")
        if record.pages:
            lines.append(f"%P {_clean(record.pages)}")
        if record.doi:
            lines.append(f"%R {_clean(record.doi)}")
        if record.abstract:
            lines.append(f"%X {_clean(record.abstract)}")
        for keyword in record.keywords:
            lines.append(f"%K {_clean(keyword)}")
        if record.url:
            lines.append(f"%U {_clean(record.url)}")
        lines.append("")
    return "\n".join(lines)
