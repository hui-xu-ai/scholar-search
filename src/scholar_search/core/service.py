"""Service facade: the only entry point transports talk to.

It owns the request lifecycle (validate → plan → execute → parse → cache) and
never exposes browser details to callers.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Sequence
from datetime import datetime
from typing import Any, Literal

from .cache import Cache
from .contracts import (
    ActionOutcome,
    BrowserAdapter,
    Channel,
    Record,
    SearchPage,
    SearchQuery,
)
from .errors import ParseError, PolicyError
from .export import to_endnote, to_ris
from .planner import Planner
from .policy import PolicyEngine
from .registry import ChannelRegistry, ChannelSpec


class ScholarService:
    def __init__(
        self,
        registry: ChannelRegistry,
        adapter_factory: Callable[[], BrowserAdapter],
        *,
        planner_factory: Callable[[BrowserAdapter], Planner],
        policy: PolicyEngine,
        cache: Cache,
        status_provider: Callable[[], dict[str, Any]] | None = None,
    ) -> None:
        self._registry = registry
        self._adapter_factory = adapter_factory
        self._planner_factory = planner_factory
        self._policy = policy
        self._cache = cache
        self._status_provider = status_provider or (lambda: {})

    # -- public surface -------------------------------------------------

    def search(self, query: SearchQuery) -> SearchPage:
        query.validate()
        spec, channel = self._resolve(query.channel)
        key = _key("search", spec, query)

        cached = self._cache.get(key)
        if cached is not None:
            return _page_from(cached)

        plan = channel.plan_search(query)
        page = channel.parse_search(_html(self._run(plan, spec)), query=query)
        self._cache.set(key, _page_to(page))
        return page

    def detail(self, url: str, *, channel: str) -> Record:
        spec, impl = self._resolve(channel)
        self._validate_detail_url(url, spec)

        key = _key("detail", spec, {"url": url})
        cached = self._cache.get(key)
        if cached is not None:
            return _record_from(cached)

        record = impl.parse_detail(_html(self._run(impl.plan_detail(url), spec)), url=url)
        self._cache.set(key, record.to_dict())
        return record

    def journal(
        self, *, issn: str, year: int, issue: str, channel: str
    ) -> SearchPage:
        spec, impl = self._resolve(channel)
        key = _key("journal", spec, {"issn": issn, "year": year, "issue": issue})

        cached = self._cache.get(key)
        if cached is not None:
            return _page_from(cached)

        plan = impl.plan_journal(issn=issn, year=year, issue=issue)
        page = impl.parse_journal(
            _html(self._run(plan, spec)), issn=issn, year=year, issue=issue
        )
        self._cache.set(key, _page_to(page))
        return page

    def export(
        self, records: Sequence[Record], *, fmt: Literal["ris", "endnote"]
    ) -> str:
        if fmt == "ris":
            return to_ris(records)
        if fmt == "endnote":
            return to_endnote(records)
        raise ValueError(f"unsupported export format: {fmt!r}")

    def status(self) -> dict[str, Any]:
        return dict(self._status_provider())

    # -- internals ------------------------------------------------------

    def _resolve(self, name: str) -> tuple[ChannelSpec, Channel]:
        spec = self._registry.select(name)
        return spec, self._registry.load(name, spec.site_version)

    def _validate_detail_url(self, url: str, spec: ChannelSpec) -> None:
        self._policy.check_url(url, spec.manifest.domains)
        path = url.split("?", 1)[0]
        prefixes = spec.manifest.detail_url_prefixes
        if prefixes and not any(prefix in path for prefix in prefixes):
            raise PolicyError(
                f"detail URL path is not allowed: {path}", rule="url.detail_path"
            )

    def _run(self, plan: Any, spec: ChannelSpec) -> tuple[ActionOutcome, ...]:
        adapter = self._adapter_factory()
        try:
            return self._planner_factory(adapter).run(plan, spec.manifest)
        finally:
            adapter.close()


# -- cache serialisation ---------------------------------------------------


def _key(kind: str, spec: ChannelSpec, payload: Any) -> str:
    raw = json.dumps(
        {"kind": kind, "channel": spec.name, "site": spec.site_version, "q": payload},
        sort_keys=True,
        ensure_ascii=False,
        default=str,
    )
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]
    return f"{kind}:{spec.name}:{spec.site_version}:{digest}"


def _page_to(page: SearchPage) -> dict[str, Any]:
    return {
        "records": [record.to_dict() for record in page.records],
        "total": page.total,
        "page": page.page,
        "page_count": page.page_count,
    }


def _page_from(payload: dict[str, Any]) -> SearchPage:
    return SearchPage(
        records=tuple(_record_from(item) for item in payload["records"]),
        total=payload.get("total"),
        page=payload.get("page"),
        page_count=payload.get("page_count"),
    )


def _record_from(payload: dict[str, Any]) -> Record:
    data = dict(payload)
    fetched = data.get("fetched_at")
    if isinstance(fetched, str):
        data["fetched_at"] = datetime.fromisoformat(fetched)
    return Record(**data)


def _html(outcomes: Sequence[ActionOutcome]) -> str:
    for outcome in reversed(outcomes):
        value = outcome.data.get("html")
        if isinstance(value, str):
            return value
    raise ParseError("plan produced no html payload")
