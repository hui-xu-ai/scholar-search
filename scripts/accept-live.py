r"""Live smoke test: run one search (optionally a detail) against the real bridge.

This is a maintainer tool, not part of the package. It talks to the running
native host directly, so it exercises the channel, the parsers and the browser
without going through an MCP client.

    $env:SCHOLAR_SEARCH_HOME = "$env:LOCALAPPDATA\scholar-search"
    python scripts/accept-live.py "IPMC" --limit 5
    python scripts/accept-live.py "IPMC" --limit 3 --detail

It spends real quota: one search is three network actions (goto/type/click),
one detail is one more. Check `scholar-search status` first.
"""

from __future__ import annotations

import argparse
import sys

from scholar_search.bootstrap import build_service
from scholar_search.core.contracts import SearchQuery


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="run one live search through the bridge")
    parser.add_argument("query", nargs="?", default="IPMC", help="keyword or expert expression")
    parser.add_argument("--limit", type=int, default=5, help="records per page (1-50)")
    parser.add_argument("--page", type=int, default=1, help="page number (1-3)")
    parser.add_argument(
        "--detail", action="store_true", help="also fetch the first record's detail"
    )
    args = parser.parse_args(argv)

    service = build_service()
    status = service.status()
    ready = status.get("bridge_ready")
    remaining = status.get("quota_remaining")
    print(f"bridge_ready={ready} quota_remaining={remaining}")
    if not status.get("bridge_ready"):
        print("native host is not answering; open the browser profile first", file=sys.stderr)
        return 2

    page = service.search(
        SearchQuery(text=args.query, channel="cnki", limit=args.limit, page=args.page)
    )
    print(f"search ok: total={page.total} page={page.page} records={len(page.records)}")
    for record in page.records:
        authors = ", ".join(record.authors[:3])
        print(f"  - {record.title} | {record.source} {record.year} | {authors} | {record.doc_type}")

    if args.detail and page.records:
        first = page.records[0]
        record = service.detail(first.url or "", channel="cnki")
        print(f"detail ok: {record.title}")
        print(
            f"  authors={len(record.authors)} year={record.year} "
            f"volume={record.volume} issue={record.issue} pages={record.pages}"
        )
        print(f"  doi={record.doi} keywords={record.keywords}")
        print(f"  abstract chars={len(record.abstract or '')}")
        print(f"export ris first line: {service.export([record], fmt='ris').splitlines()[0]}")

    print(f"quota_remaining now: {service.status().get('quota_remaining')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
